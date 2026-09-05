"""
Transformer-based sequence model for crypto signal generation.
Captures long-range temporal patterns that gradient boosting misses.

Architecture:
- Input projection → sinusoidal positional encoding
- Multi-head self-attention blocks
- Global average pooling → classification head
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

logger = logging.getLogger(__name__)


class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 512):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model)
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.pe[:, : x.size(1)]


class TransformerSignalModel(nn.Module):
    def __init__(
        self,
        n_features: int,
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 3,
        dim_ff: int = 128,
        dropout: float = 0.2,
        n_classes: int = 3,
    ):
        super().__init__()
        self.input_proj = nn.Linear(n_features, d_model)
        self.pos_enc = PositionalEncoding(d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_ff,
            dropout=dropout,
            batch_first=True,
            activation="gelu",
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.head = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model // 2, n_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq_len, n_features)
        x = self.input_proj(x)
        x = self.pos_enc(x)
        x = self.encoder(x)
        x = x.mean(dim=1)  # global avg pool
        return self.head(x)


class TransformerSignalWrapper:
    """Wrapper that handles training, inference, and persistence for the Transformer model."""

    def __init__(
        self,
        seq_len: int = 60,
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 3,
        epochs: int = 30,
        batch_size: int = 64,
        lr: float = 1e-3,
        device: Optional[str] = None,
    ):
        self.seq_len = seq_len
        self.epochs = epochs
        self.batch_size = batch_size
        self.lr = lr
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.config = {
            "d_model": d_model,
            "nhead": nhead,
            "num_layers": num_layers,
        }
        self.model: Optional[TransformerSignalModel] = None
        self.feature_names: list[str] = []
        self.metrics: dict = {}

    def _create_sequences(
        self, X: np.ndarray, y: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        xs, ys = [], []
        for i in range(len(X) - self.seq_len):
            xs.append(X[i : i + self.seq_len])
            ys.append(y[i + self.seq_len])
        return np.array(xs, dtype=np.float32), np.array(ys, dtype=np.int64)

    def train(self, X: pd.DataFrame, y: pd.Series) -> dict:
        self.feature_names = list(X.columns)
        Xv = X.values.astype(np.float32)
        yv = y.map({-1: 0, 0: 1, 1: 2}).values
        Xv = np.nan_to_num(Xv, nan=0.0, posinf=0.0, neginf=0.0)

        Xs, ys = self._create_sequences(Xv, yv)
        if len(Xs) == 0:
            return {"error": "not enough data"}

        # Normalize
        self.mean = Xs.mean(axis=(0, 1))
        self.std = Xs.std(axis=(0, 1)) + 1e-8
        Xs = (Xs - self.mean) / self.std

        # Train/val split (last 20% as val)
        split = int(len(Xs) * 0.8)
        X_tr, X_val = Xs[:split], Xs[split:]
        y_tr, y_val = ys[:split], ys[split:]

        train_ds = TensorDataset(torch.from_numpy(X_tr), torch.from_numpy(y_tr))
        val_ds = TensorDataset(torch.from_numpy(X_val), torch.from_numpy(y_val))
        train_dl = DataLoader(
            train_ds, batch_size=self.batch_size, shuffle=True, drop_last=True
        )
        val_dl = DataLoader(val_ds, batch_size=self.batch_size)

        self.model = TransformerSignalModel(
            n_features=X.shape[1], **self.config
        ).to(self.device)

        opt = torch.optim.AdamW(self.model.parameters(), lr=self.lr, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=self.epochs)
        criterion = nn.CrossEntropyLoss()

        best_val_loss = float("inf")
        best_state = None
        for epoch in range(self.epochs):
            self.model.train()
            train_loss = 0
            for xb, yb in train_dl:
                xb, yb = xb.to(self.device), yb.to(self.device)
                opt.zero_grad()
                out = self.model(xb)
                loss = criterion(out, yb)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                opt.step()
                train_loss += loss.item()
            scheduler.step()

            self.model.eval()
            val_loss = 0
            with torch.no_grad():
                for xb, yb in val_dl:
                    xb, yb = xb.to(self.device), yb.to(self.device)
                    out = self.model(xb)
                    val_loss += criterion(out, yb).item()
            val_loss /= max(len(val_dl), 1)

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}

            if (epoch + 1) % 5 == 0:
                logger.info("Transformer epoch %d/%d val_loss=%.4f", epoch + 1, self.epochs, val_loss)

        if best_state is not None:
            self.model.load_state_dict(best_state)

        self.metrics = {
            "best_val_loss": float(best_val_loss),
            "epochs": self.epochs,
            "n_sequences": int(len(Xs)),
        }
        return self.metrics

    @torch.no_grad()
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Model not trained")
        Xv = X.values.astype(np.float32)
        Xv = np.nan_to_num(Xv, nan=0.0, posinf=0.0, neginf=0.0)
        Xv = (Xv - self.mean) / self.std

        # Use last seq_len rows
        if len(Xv) < self.seq_len:
            pad = np.zeros((self.seq_len - len(Xv), Xv.shape[1]), dtype=np.float32)
            Xv = np.concatenate([pad, Xv], axis=0)
        seq = Xv[-self.seq_len :].reshape(1, self.seq_len, -1)
        seq_t = torch.from_numpy(seq).to(self.device)
        self.model.eval()
        out = self.model(seq_t)
        proba = torch.softmax(out, dim=-1).cpu().numpy()
        return proba

    def save(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "state_dict": self.model.state_dict(),
                "config": self.config,
                "feature_names": self.feature_names,
                "mean": self.mean.tolist(),
                "std": self.std.tolist(),
                "seq_len": self.seq_len,
                "metrics": self.metrics,
            },
            path,
        )

    def load(self, path: str) -> None:
        ckpt = torch.load(path, map_location=self.device)
        self.config = ckpt["config"]
        self.feature_names = ckpt["feature_names"]
        self.mean = np.array(ckpt["mean"])
        self.std = np.array(ckpt["std"])
        self.seq_len = ckpt["seq_len"]
        self.metrics = ckpt.get("metrics", {})
        self.model = TransformerSignalModel(
            n_features=len(self.feature_names), **self.config
        ).to(self.device)
        self.model.load_state_dict(ckpt["state_dict"])
        self.model.eval()
