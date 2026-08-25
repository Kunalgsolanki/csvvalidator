import { useCallback, useEffect, useState } from 'react'
import { api } from './api'

const initialPage = { items: [], total: 0, page: 1, page_size: 10 }
const size = (bytes) => `${(bytes / 1024).toFixed(bytes < 1024 * 1024 ? 1 : 2)} ${bytes < 1024 * 1024 ? 'KB' : 'MB'}`



function App() {
  const [jobs, setJobs] = useState([]); const [job, setJob] = useState(null); const [records, setRecords] = useState(initialPage)
  const [file, setFile] = useState(null); const [error, setError] = useState(''); const [uploading, setUploading] = useState(false)
  const [search, setSearch] = useState(''); const [invalidOnly, setInvalidOnly] = useState(false); const [page, setPage] = useState(1)
  
  const loadJobs = useCallback(async () => { try { const data = await api.jobs(); setJobs(data); if (!job && data[0]) setJob(data[0]) } catch { setError('Could not load import history. Is the API running?') } }, [job])
    
  useEffect(() => { loadJobs() }, [])
  const loadRecords = useCallback(async () => { if (!job || job.status !== 'completed') return; try { setRecords(await api.records(job.id, { page, page_size: 10, search, invalid_only: invalidOnly })) } catch (e) { setError(e.message) } }, [job, page, search, invalidOnly])

  useEffect(() => { loadRecords() }, [loadRecords])
  
  useEffect(() => { if (job?.status === 'pending' || job?.status === 'processing') { const timer = setInterval(async () => { const current = await api.job(job.id); setJob(current); loadJobs(); }, 1000); return () => clearInterval(timer) } }, [job, loadJobs])
  const selectFile = (next) => { setError(''); setFile(next?.[0] || null) }
  const upload = async () => { if (!file) return setError('Choose a CSV file before uploading.'); setUploading(true); setError(''); try { const created = await api.upload(file); setJob(created); setPage(1); setSearch(''); setInvalidOnly(false); setFile(null); loadJobs() } catch (e) { setError(e.message) } finally { setUploading(false) } }
  const chooseJob = (selected) => { setJob(selected); setPage(1); setSearch(''); setInvalidOnly(false) }
  return <main>
    <header><div><p className="eyebrow">ONEPRISM / DATA OPS</p><h1>Customer import validator</h1><p className="subtle">Upload a customer CSV, review every issue, and export clean records.</p></div><span className="live">● Persistent import history</span></header>
    <section className="layout"><aside><h2>New import</h2><label className="dropzone" onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); selectFile(e.dataTransfer.files) }}><input type="file" accept=".csv,text/csv" onChange={e => selectFile(e.target.files)} /> <strong>Drop CSV here</strong><span>or choose a file · 5 MB max</span></label>{file && <p className="file">{file.name} <span>{size(file.size)}</span></p>}<button onClick={upload} disabled={uploading}>{uploading ? 'Creating import…' : 'Upload and validate'}</button>{error && <p className="error">{error}</p>}
      <div className="history"><h2>Previous imports</h2>{jobs.length === 0 ? <p className="subtle">No imports yet.</p> : jobs.map(item => <button className={`history-item ${job?.id === item.id ? 'active' : ''}`} key={item.id} onClick={() => chooseJob(item)}><span>{item.filename}</span><small>{item.status} · {item.total_records} rows</small></button>)}</div></aside>
      <section className="content">{!job ? <div className="empty"><h2>Ready when you are</h2><p>Select a CSV to start your first validation run.</p></div> : <><div className="job-title"><div><p className="eyebrow">IMPORT RESULT</p><h2>{job.filename}</h2><p className={`status ${job.status}`}>{job.status}</p>{job.error_message && <p className="error">{job.error_message}</p>}</div>{job.status === 'completed' && <a className="button-link" href={api.validDownloadUrl(job.id)}>Download valid CSV</a>}</div>
        <div className="metrics">{[['Total', job.total_records], ['Valid', job.valid_records], ['Invalid', job.invalid_records], ['Duplicates', job.duplicate_records]].map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>
        {job.status !== 'completed' ? <div className="empty"><h2>{job.status === 'failed' ? 'Import failed' : 'Processing rows…'}</h2><p>{job.status === 'failed' ? 'Fix the issue and upload the file again.' : 'This page will update automatically.'}</p></div> : <><div className="toolbar"><input value={search} placeholder="Search name, email, company, city" onChange={e => { setSearch(e.target.value); setPage(1) }} /><label><input type="checkbox" checked={invalidOnly} onChange={e => { setInvalidOnly(e.target.checked); setPage(1) }} /> Invalid only</label></div><div className="table-wrap"><table><thead><tr><th>Row</th><th>Customer</th><th>Contact</th><th>Company / city</th><th>Validation reasons</th></tr></thead><tbody>{records.items.map(r => <tr key={r.row_number}><td>{r.row_number}</td><td><strong>{r.name || '—'}</strong></td><td>{r.email || '—'}<br /><small>{r.phone || '—'}</small></td><td>{r.company || '—'}<br /><small>{r.city || '—'}</small></td><td>{r.reasons.length ? r.reasons.map(reason => <span className="reason" key={reason}>{reason}</span>) : <span className="valid">Valid</span>}</td></tr>)}{records.items.length === 0 && <tr><td colSpan="5" className="no-results">No matching records.</td></tr>}</tbody></table></div><div className="pagination"><span>{records.total} record{records.total === 1 ? '' : 's'}</span><div><button disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</button><span>Page {page}</span><button disabled={page * records.page_size >= records.total} onClick={() => setPage(page + 1)}>Next</button></div></div></>}</>}</section></section>
  </main>
}
export default App
