export interface Overview {
  btc_price?: number
  btc_change?: number
  eth_price?: number
  eth_change?: number
  total_volume_24h?: number
  btc_dominance?: number
  total_market_cap?: number
  market_status?: string
}

export interface Notification {
  id: number;
  type: string;
  is_read: boolean;
  title: string;
  message?: string;
  created_at: string;
}
