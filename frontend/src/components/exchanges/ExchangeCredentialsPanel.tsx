"use client"

import { useCallback, useEffect, useState } from "react"
import { CheckCircle2, KeyRound, Loader2, LockKeyhole, ShieldAlert, Trash2, XCircle } from "lucide-react"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/Button"
import { cn } from "@/lib/utils"

interface CredentialStatus {
  exchange: "binance" | "bybit"
  label?: string | null
  configured: boolean
  last_used?: string | null
  created_at?: string | null
}

interface TradingStatus {
  default_mode: "paper"
  live_trading_enabled: boolean
  kill_switch_active: boolean
  accepting_live_orders: boolean
  configured_exchanges: string[]
}

const exchangeInfo = {
  binance: { name: "Binance Futures", note: "USDT-M Futures API key" },
  bybit: { name: "Bybit Futures", note: "Linear USDT Perpetual API key" },
} as const

export function ExchangeCredentialsPanel() {
  const [credentials, setCredentials] = useState<CredentialStatus[]>([])
  const [status, setStatus] = useState<TradingStatus | null>(null)
  const [exchange, setExchange] = useState<"binance" | "bybit">("binance")
  const [form, setForm] = useState({ api_key: "", secret_key: "", passphrase: "", label: "" })
  const [busy, setBusy] = useState<"test" | "save" | "remove" | null>(null)
  const [tested, setTested] = useState(false)
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null)

  const load = useCallback(async () => {
    try {
      const [credentialRows, trading] = await Promise.all([
        api.getExchangeCredentials(),
        api.getTradingStatus(),
      ])
      setCredentials(Array.isArray(credentialRows) ? credentialRows as CredentialStatus[] : [])
      setStatus(trading as TradingStatus)
    } catch (cause) {
      setMessage({ type: "error", text: cause instanceof Error ? cause.message : "Exchange statusu alınmadı" })
    }
  }, [])

  useEffect(() => { load() }, [load])

  const payload = {
    exchange,
    api_key: form.api_key.trim(),
    secret_key: form.secret_key.trim(),
    passphrase: form.passphrase.trim() || undefined,
    label: form.label.trim() || undefined,
  }

  function validate() {
    if (payload.api_key.length < 8 || payload.secret_key.length < 8) {
      setMessage({ type: "error", text: "API key və secret ən azı 8 simvol olmalıdır" })
      return false
    }
    return true
  }

  async function testConnection() {
    if (!validate()) return
    setBusy("test")
    setMessage(null)
    setTested(false)
    try {
      await api.testAPIKeys(payload)
      setTested(true)
      setMessage({ type: "success", text: `${exchangeInfo[exchange].name} bağlantısı təsdiqləndi. Açarlar hələ saxlanmayıb.` })
    } catch (cause) {
      setMessage({ type: "error", text: cause instanceof Error ? cause.message : "Connection test uğursuz oldu" })
    } finally {
      setBusy(null)
    }
  }

  async function saveCredentials() {
    if (!validate()) return
    setBusy("save")
    setMessage(null)
    try {
      await api.saveAPIKeys(payload)
      setForm({ api_key: "", secret_key: "", passphrase: "", label: "" })
      setTested(false)
      setMessage({ type: "success", text: "Açarlar yoxlanıldı, şifrələndi və təhlükəsiz saxlanıldı" })
      await load()
    } catch (cause) {
      setMessage({ type: "error", text: cause instanceof Error ? cause.message : "Açarlar saxlanmadı" })
    } finally {
      setBusy(null)
    }
  }

  async function removeCredentials(target: "binance" | "bybit") {
    if (!window.confirm(`${exchangeInfo[target].name} bağlantısı silinsin?`)) return
    setBusy("remove")
    setMessage(null)
    try {
      await api.removeAPIKeys(target)
      setMessage({ type: "success", text: `${exchangeInfo[target].name} bağlantısı deaktiv edildi` })
      await load()
    } catch (cause) {
      setMessage({ type: "error", text: cause instanceof Error ? cause.message : "Bağlantı silinmədi" })
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-4 lg:p-6">
      <div>
        <h1 className="flex items-center gap-2 text-lg font-semibold text-white"><KeyRound className="h-5 w-5 text-blue-400" /> Exchange bağlantıları</h1>
        <p className="mt-1 text-xs text-gray-500">API secret brauzerə geri qaytarılmır. Açarlar serverdə Fernet ilə şifrələnir.</p>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <StatusCard label="Standart rejim" value="PAPER" tone="blue" description="Live rejim avtomatik aktivləşmir" />
        <StatusCard label="Live trading" value={status?.live_trading_enabled ? "SERVER ENABLED" : "SERVER DISABLED"} tone={status?.live_trading_enabled ? "yellow" : "green"} description="Server konfiqurasiyası ilə idarə olunur" />
        <StatusCard label="Kill switch" value={status?.kill_switch_active ? "AKTİV" : "NORMAL"} tone={status?.kill_switch_active ? "red" : "green"} description={status?.accepting_live_orders ? "Live order qəbul edilə bilər" : "Live order qəbul edilmir"} />
      </div>

      {message && (
        <div className={cn("flex items-start gap-2 rounded-lg border p-3 text-xs", message.type === "success" ? "border-green-900/60 bg-green-950/30 text-green-300" : "border-red-900/60 bg-red-950/30 text-red-300")}>
          {message.type === "success" ? <CheckCircle2 className="h-4 w-4 shrink-0" /> : <XCircle className="h-4 w-4 shrink-0" />}
          {message.text}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl border border-gray-800 bg-gray-900/40 p-4">
          <h2 className="text-xs font-semibold uppercase text-gray-300">Yeni bağlantı və ya açar yeniləmə</h2>
          <div className="mt-3 grid grid-cols-2 gap-2">
            {(["binance", "bybit"] as const).map((name) => (
              <button key={name} onClick={() => { setExchange(name); setTested(false) }} className={cn("rounded-lg border p-3 text-left", exchange === name ? "border-blue-500 bg-blue-950/30" : "border-gray-800 bg-gray-950/30")}>
                <div className="text-xs font-semibold text-white">{exchangeInfo[name].name}</div>
                <div className="mt-1 text-[9px] text-gray-600">{exchangeInfo[name].note}</div>
              </button>
            ))}
          </div>
          <div className="mt-3 space-y-2">
            <Input label="Label" value={form.label} onChange={(value) => setForm({ ...form, label: value })} placeholder="Məsələn: Main Futures" />
            <Input label="API Key" value={form.api_key} onChange={(value) => { setForm({ ...form, api_key: value }); setTested(false) }} />
            <Input label="Secret Key" type="password" value={form.secret_key} onChange={(value) => { setForm({ ...form, secret_key: value }); setTested(false) }} />
            <Input label="Passphrase (lazım olarsa)" type="password" value={form.passphrase} onChange={(value) => { setForm({ ...form, passphrase: value }); setTested(false) }} />
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <Button variant="ghost" disabled={busy != null} onClick={testConnection}>
              {busy === "test" && <Loader2 className="mr-1 h-3 w-3 animate-spin" />} Test et
            </Button>
            <Button disabled={busy != null} onClick={saveCredentials}>
              {busy === "save" && <Loader2 className="mr-1 h-3 w-3 animate-spin" />} Yoxla və saxla
            </Button>
          </div>
          {tested && <div className="mt-2 text-center text-[9px] text-green-400">Connection test keçdi</div>}
        </section>

        <section className="rounded-xl border border-gray-800 bg-gray-900/40 p-4">
          <h2 className="text-xs font-semibold uppercase text-gray-300">Saxlanmış bağlantılar</h2>
          <div className="mt-3 space-y-2">
            {(["binance", "bybit"] as const).map((name) => {
              const credential = credentials.find((item) => item.exchange === name)
              return (
                <div key={name} className="flex items-center gap-3 rounded-lg border border-gray-800 bg-gray-950/40 p-3">
                  <div className={cn("rounded-lg p-2", credential ? "bg-green-950 text-green-400" : "bg-gray-800 text-gray-600")}><LockKeyhole className="h-4 w-4" /></div>
                  <div className="min-w-0 flex-1">
                    <div className="text-xs font-semibold text-white">{exchangeInfo[name].name}</div>
                    <div className="mt-0.5 text-[9px] text-gray-600">{credential ? credential.label || "Şifrələnmiş credential mövcuddur" : "Qoşulmayıb"}</div>
                    {credential?.last_used && <div className="text-[9px] text-gray-700">Son istifadə: {new Date(credential.last_used).toLocaleString("az")}</div>}
                  </div>
                  {credential && <Button variant="ghost" size="sm" disabled={busy != null} onClick={() => removeCredentials(name)}><Trash2 className="h-3.5 w-3.5 text-red-400" /></Button>}
                </div>
              )
            })}
          </div>
          <div className="mt-4 flex gap-2 rounded-lg border border-yellow-900/40 bg-yellow-950/20 p-3 text-[10px] text-yellow-200">
            <ShieldAlert className="h-4 w-4 shrink-0" />
            Withdrawal icazəsi olmayan, yalnız futures trade üçün ayrıca API key istifadə edin. IP whitelist aktivləşdirilməsi tövsiyə olunur.
          </div>
        </section>
      </div>
    </div>
  )
}

function Input({ label, value, onChange, type = "text", placeholder }: { label: string; value: string; onChange: (value: string) => void; type?: string; placeholder?: string }) {
  return <label className="block"><span className="mb-1 block text-[9px] uppercase text-gray-500">{label}</span><input type={type} value={value} placeholder={placeholder} autoComplete="off" onChange={(event) => onChange(event.target.value)} className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 font-mono text-xs text-white outline-none focus:border-blue-500" /></label>
}

function StatusCard({ label, value, description, tone }: { label: string; value: string; description: string; tone: "blue" | "green" | "yellow" | "red" }) {
  const colors = { blue: "text-blue-400", green: "text-green-400", yellow: "text-yellow-400", red: "text-red-400" }
  return <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-4"><div className="text-[9px] uppercase text-gray-600">{label}</div><div className={cn("mt-2 font-mono text-sm font-bold", colors[tone])}>{value}</div><div className="mt-1 text-[9px] text-gray-600">{description}</div></div>
}
