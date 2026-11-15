const API = {
  async json(url) {
    const r = await fetch(url, { cache: "no-store" });
    let payload;
    try {
      payload = await r.json();
    } catch (err) {
      throw new Error(`HTTP ${r.status}`);
    }
    if (!r.ok || payload.error) throw new Error(payload.error || `HTTP ${r.status}`);
    return payload;
  },
  sites() {
    return this.json("/api/sites");
  },
  scenario(params) {
    return this.json("/api/scenario?" + new URLSearchParams(params));
  },
  compare(items) {
    return this.json("/api/compare?items=" + encodeURIComponent(JSON.stringify(items)));
  },
  phase(params) {
    return this.json("/api/phase?" + new URLSearchParams(params));
  },
  health() {
    return this.json("/api/health");
  },
  illuminationURL(params) {
    return "/api/illumination?" + new URLSearchParams(params);
  },
  illuminationStats(params) {
    return this.json("/api/illumination?" + new URLSearchParams({ ...params, format: "json" }));
  },
};
