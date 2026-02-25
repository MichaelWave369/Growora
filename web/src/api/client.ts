export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const profileId = localStorage.getItem('growora_profile_id')
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (profileId) headers['X-Growora-Profile'] = profileId
  const res = await fetch(path, { headers, ...options })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
