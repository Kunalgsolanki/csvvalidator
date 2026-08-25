function formatFileSize(bytes) {
  const unit = bytes < 1024 * 1024 ? 'KB' : 'MB'
  const precision = unit === 'KB' ? 1 : 2
  return `${(bytes / 1024).toFixed(precision)} ${unit}`
}

export function ImportSidebar({
  jobs,
  selectedJobId,
  file,
  uploading,
  error,
  onChooseFile,
  onUpload,
  onChooseJob,
}) {
  return (
    <aside>
      <h2>New import</h2>

      <label
        className="dropzone"
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault()
          onChooseFile(event.dataTransfer.files)
        }}
      >
        <input type="file" accept=".csv,text/csv" onChange={(event) => onChooseFile(event.target.files)} />
        <strong>Drop CSV here</strong>
        <span>or choose a file · 5 MB max</span>
      </label>

      {file && <p className="file">{file.name} <span>{formatFileSize(file.size)}</span></p>}
      <button onClick={onUpload} disabled={uploading}>
        {uploading ? 'Creating import…' : 'Upload and validate'}
      </button>
      {error && <p className="error">{error}</p>}

      <div className="history">
        <h2>Previous imports</h2>
        {jobs.length === 0 ? (
          <p className="subtle">No imports yet.</p>
        ) : (
          jobs.map((job) => (
            <button
              className={`history-item ${selectedJobId === job.id ? 'active' : ''}`}
              key={job.id}
              onClick={() => onChooseJob(job)}
            >
              <span>{job.filename}</span>
              <small>{job.status} · {job.total_records} rows</small>
            </button>
          ))
        )}
      </div>
    </aside>
  )
}
