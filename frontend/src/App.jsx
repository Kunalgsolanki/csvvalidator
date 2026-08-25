import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import { ImportResults } from './components/ImportResults'
import { ImportSidebar } from './components/ImportSidebar'

const EMPTY_RECORD_PAGE = { items: [], total: 0, page: 1, page_size: 10 }

function App() {
  // Page state: selected import, selected file, filters, and visible records.
  const [jobs, setJobs] = useState([])
  const [job, setJob] = useState(null)
  const [records, setRecords] = useState(EMPTY_RECORD_PAGE)
  const [file, setFile] = useState(null)
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [search, setSearch] = useState('')
  const [invalidOnly, setInvalidOnly] = useState(false)
  const [page, setPage] = useState(1)

  // API loading stays here; display components only receive props.
  const loadJobs = useCallback(async () => {
    try {
      const imports = await api.jobs()
      setJobs(imports)
      setJob((currentJob) => currentJob || imports[0] || null)
    } catch {
      setError('Could not load import history. Is the API running?')
    }
  }, [])

  const loadRecords = useCallback(async () => {
    if (!job || job.status !== 'completed') return

    try {
      const recordPage = await api.records(job.id, {
        page,
        page_size: 10,
        search,
        invalid_only: invalidOnly,
      })
      setRecords(recordPage)
    } catch (requestError) {
      setError(requestError.message)
    }
  }, [invalidOnly, job, page, search])

  useEffect(() => { loadJobs() }, [loadJobs])
  useEffect(() => { loadRecords() }, [loadRecords])

  // Keep the UI updated while the backend processes an upload.
  useEffect(() => {
    if (!job || !['pending', 'processing'].includes(job.status)) return undefined

    const timer = setInterval(async () => {
      try {
        setJob(await api.job(job.id))
        await loadJobs()
      } catch (requestError) {
        setError(requestError.message)
      }
    }, 1000)

    return () => clearInterval(timer)
  }, [job, loadJobs])

  const resetRecordFilters = () => {
    setPage(1)
    setSearch('')
    setInvalidOnly(false)
  }

  const chooseFile = (files) => {
    setError('')
    setFile(files?.[0] || null)
  }

  const uploadFile = async () => {
    if (!file) {
      setError('Choose a CSV file before uploading.')
      return
    }

    setUploading(true)
    setError('')
    try {
      const createdJob = await api.upload(file)
      setJob(createdJob)
      setFile(null)
      resetRecordFilters()
      await loadJobs()
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setUploading(false)
    }
  }

  const chooseJob = (selectedJob) => {
    setJob(selectedJob)
    resetRecordFilters()
  }

  const changeSearch = (value) => {
    setSearch(value)
    setPage(1)
  }

  const changeInvalidOnly = (value) => {
    setInvalidOnly(value)
    setPage(1)
  }

  return (
    <main>
      <AppHeader />
      <section className="layout">
        <ImportSidebar
          jobs={jobs}
          selectedJobId={job?.id}
          file={file}
          uploading={uploading}
          error={error}
          onChooseFile={chooseFile}
          onUpload={uploadFile}
          onChooseJob={chooseJob}
        />
        <ImportResults
          job={job}
          records={records}
          search={search}
          invalidOnly={invalidOnly}
          onSearchChange={changeSearch}
          onInvalidOnlyChange={changeInvalidOnly}
          onPageChange={setPage}
          downloadUrl={job ? api.validDownloadUrl(job.id) : ''}
        />
      </section>
    </main>
  )
}

function AppHeader() {
  return (
    <header>
      <div>
        <p className="eyebrow">ONEPRISM / DATA OPS</p>
        <h1>Customer import validator</h1>
        <p className="subtle">Upload a customer CSV, review every issue, and export clean records.</p>
      </div>
      <span className="live">● Persistent import history</span>
    </header>
  )
}

export default App
