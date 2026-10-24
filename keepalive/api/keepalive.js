// Daily Vercel cron (see ../vercel.json). Free-plan Supabase projects pause
// after ~7 days without activity, which breaks the booth's QR uploads between
// events. This runs a tiny database query: public.keepalive() → now().
const SUPABASE_URL = 'https://wdzsjgwhhohxlrzxojgq.supabase.co';
// Public anon key — the same one the booth page ships; safe to commit
const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndkenNqZ3doaG9oeGxyenhvamdxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUzOTkyOTYsImV4cCI6MjA5MDk3NTI5Nn0.K677qTL0E813GSkW9HuALOCLyKh86YOSAgS1RvS_odw';

module.exports = async (req, res) => {
  try {
    const r = await fetch(`${SUPABASE_URL}/rest/v1/rpc/keepalive`, {
      method: 'POST',
      headers: { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}`, 'Content-Type': 'application/json' },
      body: '{}'
    });
    const body = await r.text();
    console.log('[keepalive]', r.status, body);
    res.status(r.ok ? 200 : 502).json({ ok: r.ok, supabaseStatus: r.status, databaseTime: r.ok ? JSON.parse(body) : body });
  } catch (err) {
    console.error('[keepalive] failed:', err.message);
    res.status(502).json({ ok: false, error: err.message });
  }
};
