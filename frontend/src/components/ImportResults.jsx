function Metrics({ job }) {
  const metrics = [
    ['Total', job.total_records],
    ['Valid', job.valid_records],
    ['Invalid', job.invalid_records],
    ['Duplicates', job.duplicate_records],
  ]

  return <div className="metrics">{metrics.map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>
}

function RecordsTable({ records }) {
  return (
    <>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Row</th><th>Customer</th><th>Contact</th><th>Company / city</th><th>Validation reasons</th></tr></thead>
          <tbody>
            {records.items.map((record) => (
              <tr key={record.row_number}>
                <td>{record.row_number}</td>
                <td><strong>{record.name || '—'}</strong></td>
                <td>{record.email || '—'}<br /><small>{record.phone || '—'}</small></td>
                <td>{record.company || '—'}<br /><small>{record.city || '—'}</small></td>
                <td>{record.reasons.length ? record.reasons.map((reason) => <span className="reason" key={reason}>{reason}</span>) : <span className="valid">Valid</span>}</td>
              </tr>
            ))}
            {records.items.length === 0 && <tr><td colSpan="5" className="no-results">No matching records.</td></tr>}
          </tbody>
        </table>
      </div>
      <div className="pagination">
        <span>{records.total} record{records.total === 1 ? '' : 's'}</span>
        <div>
          <button disabled={records.page === 1} onClick={() => records.onPageChange(records.page - 1)}>Previous</button>
          <span>Page {records.page}</span>
          <button disabled={records.page * records.page_size >= records.total} onClick={() => records.onPageChange(records.page + 1)}>Next</button>
        </div>
      </div>
    </>
  )
}

export function ImportResults({ job, records, search, invalidOnly, onSearchChange, onInvalidOnlyChange, onPageChange, downloadUrl }) {
  if (!job) {
    return <section className="content"><EmptyState title="Ready when you are" message="Select a CSV to start your first validation run." /></section>
  }

  const isCompleted = job.status === 'completed'
  return (
    <section className="content">
      <div className="job-title">
        <div>
          <p className="eyebrow">IMPORT RESULT</p>
          <h2>{job.filename}</h2>
          <p className={`status ${job.status}`}>{job.status}</p>
          {job.error_message && <p className="error">{job.error_message}</p>}
        </div>
        {isCompleted && <a className="button-link" href={downloadUrl}>Download valid CSV</a>}
      </div>

      <Metrics job={job} />
      {!isCompleted ? (
        <EmptyState
          title={job.status === 'failed' ? 'Import failed' : 'Processing rows…'}
          message={job.status === 'failed' ? 'Fix the issue and upload the file again.' : 'This page will update automatically.'}
        />
      ) : (
        <>
          <div className="toolbar">
            <input value={search} placeholder="Search name, email, company, city" onChange={(event) => onSearchChange(event.target.value)} />
            <label><input type="checkbox" checked={invalidOnly} onChange={(event) => onInvalidOnlyChange(event.target.checked)} /> Invalid only</label>
          </div>
          <RecordsTable records={{ ...records, onPageChange }} />
        </>
      )}
    </section>
  )
}

function EmptyState({ title, message }) {
  return <div className="empty"><h2>{title}</h2><p>{message}</p></div>
}
