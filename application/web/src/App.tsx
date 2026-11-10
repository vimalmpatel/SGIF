import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowDownToLine,
  ArrowUpRight,
  Boxes,
  Check,
  ChevronDown,
  CircleHelp,
  Clock3,
  Database,
  FileUp,
  LayoutDashboard,
  LogOut,
  Network,
  Plus,
  RefreshCw,
  ShieldCheck,
  ShieldHalf,
  X,
} from "lucide-react";
import { api, type Asset, type EventRecord, type EventSource, initializeIdentity, signOut, userRoles } from "./api";

type View = "overview" | "events" | "assets";
type LoadState = "loading" | "ready" | "error";

const severityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };

function formatTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function App() {
  const [identityReady, setIdentityReady] = useState(false);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [events, setEvents] = useState<EventRecord[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [view, setView] = useState<View>("overview");
  const [source, setSource] = useState<EventSource>("suricata");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isImporting, setIsImporting] = useState(false);
  const [showAssetForm, setShowAssetForm] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const roles = userRoles();
  const canOperate = roles.includes("sgif_operator") || roles.includes("sgif_admin");

  useEffect(() => {
    let active = true;
    initializeIdentity()
      .then(() => {
        if (active) setIdentityReady(true);
      })
      .catch(() => {
        if (active) {
          setLoadState("error");
          setError("Identity service is unavailable. Check the local lab stack.");
        }
      });
    return () => {
      active = false;
    };
  }, []);

  async function refresh(): Promise<void> {
    setLoadState("loading");
    setError("");
    try {
      const [nextAssets, nextEvents] = await Promise.all([api.assets(), api.events()]);
      setAssets(nextAssets);
      setEvents(nextEvents);
      setLoadState("ready");
    } catch (requestError) {
      setLoadState("error");
      setError(requestError instanceof Error ? requestError.message : "Unable to load SGIF data");
    }
  }

  useEffect(() => {
    if (identityReady) void refresh();
  }, [identityReady]);

  const recentEvents = useMemo(
    () => [...events].sort((left, right) => severityOrder[left.severity] - severityOrder[right.severity]
      || right.observed_at.localeCompare(left.observed_at)).slice(0, 8),
    [events],
  );
  const urgentCount = events.filter((event) => event.severity === "critical" || event.severity === "high").length;
  const sourceCounts = events.reduce<Record<string, number>>((counts, event) => {
    counts[event.source] = (counts[event.source] ?? 0) + 1;
    return counts;
  }, {});

  async function importFile(file?: File): Promise<void> {
    if (!file) return;
    setMessage("");
    setError("");
    if (file.size > 1_000_000) {
      setError("Choose a JSONL file smaller than 1 MB.");
      return;
    }
    setIsImporting(true);
    try {
      const result = await api.importEvents(source, await file.text());
      setMessage(`${result.accepted} new event(s) imported; ${result.duplicates} duplicate(s) skipped.`);
      await refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Import failed");
    } finally {
      setIsImporting(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function createAsset(asset: Omit<Asset, "asset_id"> & { asset_id: string }): Promise<void> {
    setError("");
    setMessage("");
    try {
      await api.createAsset(asset);
      setShowAssetForm(false);
      setMessage(`Asset ${asset.asset_id} added.`);
      await refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to create asset");
    }
  }

  if (!identityReady && loadState !== "error") {
    return <div className="identity-gate"><ShieldHalf aria-hidden="true" /><span>Connecting to SGIF Lab Identity</span><span className="gate-pulse" /></div>;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#overview" onClick={() => setView("overview")}>
          <span className="brand-mark"><ShieldHalf size={22} strokeWidth={2.2} /></span>
          <span><strong>SGIF</strong><small>GRID SECURITY</small></span>
        </a>
        <div className="site-switcher">
          <span className="site-icon"><Network size={16} /></span>
          <span className="site-name"><strong>Renewable Lab</strong><small>LOCAL ENVIRONMENT</small></span>
          <ChevronDown size={15} />
        </div>
        <p className="nav-label">WORKSPACE</p>
        <nav className="main-nav" aria-label="Main navigation">
          <button className={view === "overview" ? "nav-item active" : "nav-item"} onClick={() => setView("overview")}>
            <LayoutDashboard size={17} /> Overview
          </button>
          <button className={view === "events" ? "nav-item active" : "nav-item"} onClick={() => setView("events")}>
            <Activity size={17} /> Event stream <span className="nav-count">{events.length}</span>
          </button>
          <button className={view === "assets" ? "nav-item active" : "nav-item"} onClick={() => setView("assets")}>
            <Boxes size={17} /> Asset inventory <span className="nav-count">{assets.length}</span>
          </button>
        </nav>
        <div className="sidebar-bottom">
          <div className="connection-state"><span className="status-dot" /><span><strong>Lab profile</strong><small>Passive data only</small></span></div>
          <div className="user-row">
            <div className="user-avatar">{roles.includes("sgif_admin") ? "A" : canOperate ? "O" : "R"}</div>
            <span className="user-details"><strong>{canOperate ? "Lab operator" : "Read-only user"}</strong><small>{roles.includes("sgif_admin") ? "ADMIN" : canOperate ? "OPERATOR" : "READER"}</small></span>
            <button className="icon-button logout-button" title="Sign out" aria-label="Sign out" onClick={signOut}><LogOut size={16} /></button>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb"><span>SGIF</span><span className="crumb-slash">/</span><strong>{view === "overview" ? "Overview" : view === "events" ? "Event stream" : "Asset inventory"}</strong></div>
          <div className="topbar-actions">
            <span className="lab-badge"><span /> LAB / OFFLINE DATA</span>
            <button className="icon-button" title="Refresh data" aria-label="Refresh data" onClick={() => void refresh()} disabled={loadState === "loading"}><RefreshCw size={17} className={loadState === "loading" ? "spin" : ""} /></button>
            <button className="help-button" title="About SGIF Lab" aria-label="About SGIF Lab"><CircleHelp size={17} /></button>
          </div>
        </header>

        <div className="page-content">
          <section className="page-heading">
            <div>
              <p className="eyebrow">SECURITY OPERATIONS <span>•</span> LAB PROFILE</p>
              <h1>{view === "overview" ? "Operations overview" : view === "events" ? "Event stream" : "Asset inventory"}</h1>
              <p className="page-subtitle">{view === "assets" ? "A manually maintained register for your lab environment." : "Review imported telemetry and site inventory in one place."}</p>
            </div>
            <div className="heading-actions">
              {canOperate && view !== "assets" && <ImportControl source={source} setSource={setSource} onChoose={() => fileInput.current?.click()} isImporting={isImporting} />}
              {canOperate && view === "assets" && <button className="button button-primary" onClick={() => setShowAssetForm(true)}><Plus size={16} /> Add asset</button>}
              <input ref={fileInput} className="visually-hidden" type="file" accept=".jsonl,.json,application/json" onChange={(event) => void importFile(event.target.files?.[0])} />
            </div>
          </section>

          {(message || error) && <div className={error ? "notice notice-error" : "notice notice-success"} role="status">{error ? <AlertTriangle size={17} /> : <Check size={17} />}{error || message}<button className="icon-button" aria-label="Dismiss message" onClick={() => { setError(""); setMessage(""); }}><X size={15} /></button></div>}

          {loadState === "loading" && <div className="loading-line"><span className="gate-pulse" /> Loading lab data</div>}

          {view === "overview" && <>
            <section className="metric-grid" aria-label="Summary metrics">
              <Metric icon={<Boxes size={17} />} label="REGISTERED ASSETS" value={String(assets.length).padStart(2, "0")} note="MANUALLY INVENTORIED" tone="green" />
              <Metric icon={<Activity size={17} />} label="IMPORTED EVENTS" value={String(events.length).padStart(2, "0")} note="FROM LOCAL JSONL FILES" tone="blue" />
              <Metric icon={<AlertTriangle size={17} />} label="HIGH / CRITICAL" value={String(urgentCount).padStart(2, "0")} note="SOURCE SEVERITY ONLY" tone="red" />
              <Metric icon={<Database size={17} />} label="DATA SOURCES" value={String(Object.keys(sourceCounts).length).padStart(2, "0")} note="WAZUH · SURICATA · ZEEK" tone="yellow" />
            </section>
            <div className="section-row">
              <div><p className="section-kicker">LATEST ACTIVITY</p><h2>Imported events</h2></div>
              <button className="text-button" onClick={() => setView("events")}>View event stream <ArrowUpRight size={15} /></button>
            </div>
            <EventTable events={recentEvents} loadState={loadState} />
            <section className="boundary-banner">
              <div className="boundary-icon"><ShieldCheck size={18} /></div>
              <div><strong>Passive lab workflow</strong><p>Events are imported from files. SGIF does not capture traffic or issue commands to site equipment.</p></div>
              <span className="boundary-tag">NO CONTROL PATH</span>
            </section>
          </>}

          {view === "events" && <>
            <div className="table-toolbar"><span>{events.length} RECORDS <span className="toolbar-muted">· newest first</span></span><span className="table-source-label"><Clock3 size={14} /> Timestamp shown in local time</span></div>
            <EventTable events={events} loadState={loadState} expanded />
          </>}

          {view === "assets" && <AssetTable assets={assets} loadState={loadState} />}

          <footer className="page-footer"><span>SGIF LAB <span className="footer-separator">/</span> LOCAL DEVELOPMENT</span><span>Event priority reflects source severity; not an incident verdict.</span></footer>
        </div>
      </main>
      {showAssetForm && <AssetForm onClose={() => setShowAssetForm(false)} onCreate={createAsset} />}
    </div>
  );
}

function Metric({ icon, label, value, note, tone }: { icon: React.ReactNode; label: string; value: string; note: string; tone: string }) {
  return <div className={`metric metric-${tone}`}><div className="metric-top"><span className="metric-icon">{icon}</span><span className="metric-label">{label}</span></div><strong className="metric-value">{value}</strong><span className="metric-note">{note}</span></div>;
}

function ImportControl({ source, setSource, onChoose, isImporting }: { source: EventSource; setSource: (source: EventSource) => void; onChoose: () => void; isImporting: boolean }) {
  return <div className="import-control"><label className="select-wrap"><span className="visually-hidden">Source format</span><select value={source} onChange={(event) => setSource(event.target.value as EventSource)}><option value="suricata">Suricata EVE</option><option value="zeek">Zeek conn.log</option><option value="wazuh">Wazuh alerts</option></select><ChevronDown size={14} /></label><button className="button button-primary" onClick={onChoose} disabled={isImporting}>{isImporting ? <RefreshCw className="spin" size={16} /> : <FileUp size={16} />}{isImporting ? "Importing" : "Import JSONL"}</button></div>;
}

function EventTable({ events, loadState, expanded = false }: { events: EventRecord[]; loadState: LoadState; expanded?: boolean }) {
  if (loadState === "error") return <div className="empty-state"><AlertTriangle size={22} /><strong>Data unavailable</strong><span>Check the API and database connection.</span></div>;
  if (!events.length && loadState !== "loading") return <div className="empty-state"><ArrowDownToLine size={22} /><strong>No events imported</strong><span>Import a synthetic or authorized JSONL export to populate this view.</span></div>;
  return <div className="table-scroll"><table className={expanded ? "data-table expanded-table" : "data-table"}><thead><tr><th>TIME</th><th>SEVERITY</th><th>SOURCE</th><th>EVENT</th><th>NETWORK OBSERVATION</th></tr></thead><tbody>{events.map((event) => <tr key={event.id}><td className="mono time-cell">{formatTime(event.observed_at)}</td><td><span className={`severity severity-${event.severity}`}>{event.severity}</span></td><td><span className={`source-tag source-${event.source}`}>{event.source}</span></td><td><span className="event-summary">{event.summary}</span><small className="event-type">{event.event_type}{event.sensor ? ` · ${event.sensor}` : ""}</small></td><td className="mono network-cell">{event.src_ip ?? "—"}{event.src_port ? `:${event.src_port}` : ""}<span className="flow-arrow"> → </span>{event.dest_ip ?? "—"}{event.dest_port ? `:${event.dest_port}` : ""}<span className="protocol">{event.protocol ?? ""}</span></td></tr>)}</tbody></table></div>;
}

function AssetTable({ assets, loadState }: { assets: Asset[]; loadState: LoadState }) {
  if (!assets.length && loadState !== "loading") return <div className="empty-state"><Boxes size={22} /><strong>Inventory is empty</strong><span>Add fictional lab assets or authorized site records stored outside this public repository.</span></div>;
  return <div className="table-scroll"><table className="data-table asset-table"><thead><tr><th>ASSET ID</th><th>NAME</th><th>TYPE</th><th>ZONE</th><th>CRITICALITY</th><th>OWNER ROLE</th></tr></thead><tbody>{assets.map((asset) => <tr key={asset.asset_id}><td className="mono asset-id">{asset.asset_id}</td><td>{asset.name}</td><td>{asset.asset_type}</td><td>{asset.zone}</td><td><span className={`severity severity-${asset.criticality}`}>{asset.criticality}</span></td><td>{asset.owner}</td></tr>)}</tbody></table></div>;
}

function AssetForm({ onClose, onCreate }: { onClose: () => void; onCreate: (asset: Omit<Asset, "asset_id"> & { asset_id: string }) => Promise<void> }) {
  const [pending, setPending] = useState(false);
  async function submit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setPending(true);
    const data = new FormData(event.currentTarget);
    await onCreate({
      asset_id: String(data.get("asset_id")),
      name: String(data.get("name")),
      asset_type: String(data.get("asset_type")),
      zone: String(data.get("zone")),
      criticality: String(data.get("criticality")) as Asset["criticality"],
      owner: String(data.get("owner")),
    });
    setPending(false);
  }
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><section className="asset-modal" role="dialog" aria-modal="true" aria-labelledby="asset-form-title"><header className="modal-header"><div><p className="section-kicker">INVENTORY RECORD</p><h2 id="asset-form-title">Add an asset</h2></div><button className="icon-button" aria-label="Close" onClick={onClose}><X size={18} /></button></header><form onSubmit={(event) => void submit(event)}><label>Asset ID<input name="asset_id" pattern="[A-Za-z0-9._-]+" maxLength={100} required placeholder="LAB-SENSOR-01" /></label><label>Display name<input name="name" maxLength={200} required placeholder="Passive network sensor" /></label><div className="form-two"><label>Asset type<input name="asset_type" maxLength={80} required placeholder="sensor" /></label><label>Zone<input name="zone" maxLength={80} required placeholder="monitoring-lab" /></label></div><div className="form-two"><label>Criticality<select name="criticality" defaultValue="moderate"><option value="low">Low</option><option value="moderate">Moderate</option><option value="high">High</option><option value="critical">Critical</option></select></label><label>Owner role<input name="owner" maxLength={120} required placeholder="lab-operator" /></label></div><div className="form-hint"><ShieldCheck size={15} /> Do not enter credentials, personal contact data, or sensitive public-site details.</div><div className="modal-actions"><button type="button" className="button button-quiet" onClick={onClose}>Cancel</button><button type="submit" className="button button-primary" disabled={pending}><Plus size={16} /> Save asset</button></div></form></section></div>;
}

export default App;