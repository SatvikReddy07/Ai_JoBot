"use client";
import React, { useCallback, useEffect, useState } from "react";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const API = `${BASE}/api/phase4`;
type Check = { category: string; status: string; detail: string; is_mandatory: boolean };
type Eligibility = { overall_status: string; checks: Check[]; match_score: number; sponsorship_status: string };
type Question = { question: string; answer: string; verified: boolean; mandatory: boolean };
type Application = { id: number; job_id: number; job_title: string; job_company: string; job_location: string;
  country: string; status: string; eligibility_status: string; eligibility_details: { assessment: Eligibility } | null; match_score: number; sponsorship_status: string;
  package_id: number | null; application_url: string; user_approved: boolean; date_submitted: string | null;
  updated_at: string; confirmation_reference: string | null; preparation: { questions?: Question[]; verified_fields?: Record<string,string>;
  cv_document_id?: number; cover_letter_document_id?: number }; };
type Row = { job_id: number; company: string; title: string; country: string; location: string; url: string;
  match_score: number; sponsorship_status: string; eligibility: Eligibility; application: Application | null };
type Package = { id: number; status: string; documents: { id: number; doc_type: string; filename: string; version_number: number; is_approved: boolean }[] };
type Reminder = { id: number; application_id: number; title: string; due_date: string; is_completed: boolean; is_dismissed: boolean };
type Draft = { id: number; subject: string; message_body: string; is_approved: boolean; is_sent: boolean };
type Contact = { id: number; name: string; company: string };
type History = { id: number; action: string; created_at: string; details: Record<string,unknown> };
async function request<T>(url: string, method = "GET", body?: unknown): Promise<T> {
  const response = await fetch(url, { method, headers: { "Content-Type": "application/json" },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail));
  return data as T;
}
const labels: Record<string,string> = { suitable: "Suitable", requires_review: "Requires Review",
  not_eligible: "Not Eligible", unknown_eligibility: "Unknown Eligibility" };
const pretty = (value: string) => labels[value] || value.replace(/_/g, " ");
const input = "rounded border border-slate-600 bg-slate-900 p-2 text-sm w-full";
const button = "rounded bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 px-3 py-2 text-sm";
const secondary = "rounded border border-slate-600 px-3 py-2 text-sm hover:bg-slate-800";

export function ApplicationControlCenter({ onStudio }: { onStudio: (id: number) => void }) {
  const [queue, setQueue] = useState<Row[]>([]), [apps, setApps] = useState<Application[]>([]);
  const [reminders, setReminders] = useState<Reminder[]>([]), [contacts, setContacts] = useState<Contact[]>([]);
  const [selected, setSelected] = useState<Row | null>(null), [packages, setPackages] = useState<Package[]>([]);
  const [drafts, setDrafts] = useState<Draft[]>([]), [history, setHistory] = useState<History[]>([]);
  const [view, setView] = useState("queue"), [country, setCountry] = useState(""), [employer, setEmployer] = useState("");
  const [status, setStatus] = useState(""), [eligibility, setEligibility] = useState("");
  const [sponsorship, setSponsorship] = useState(""), [minScore, setMinScore] = useState(0);
  const [since, setSince] = useState(""), [sort, setSort] = useState("score");
  const [busy, setBusy] = useState(false), [message, setMessage] = useState("");
  const [packageId, setPackageId] = useState(0), [cv, setCv] = useState(0), [letter, setLetter] = useState(0);
  const [url, setUrl] = useState(""), [reviewed, setReviewed] = useState(false), [official, setOfficial] = useState(false);
  const [acknowledge, setAcknowledge] = useState(false), [notes, setNotes] = useState("");
  const [questions, setQuestions] = useState<Question[]>([]), [fields, setFields] = useState<Record<string,string>>({});
  const [confirmation, setConfirmation] = useState(""), [submitted, setSubmitted] = useState(false);
  const [followUp, setFollowUp] = useState(true), [days, setDays] = useState(7);
  const [contactId, setContactId] = useState(0), [contactName, setContactName] = useState("");
  const [contactCompany, setContactCompany] = useState(""), [contactEmail, setContactEmail] = useState("");
  const [kind, setKind] = useState("recruiter"), [channel, setChannel] = useState("linkedin");
  const [due, setDue] = useState(""), [reminderTitle, setReminderTitle] = useState("");
  const [stage, setStage] = useState("follow_up_due");

  const load = useCallback(async () => {
    const [q, a, r, c] = await Promise.all([
      request<Row[]>(`${API}/queue`), request<Application[]>(`${API}/applications`),
      request<Reminder[]>(`${API}/reminders`), request<Contact[]>(`${API}/contacts`)]);
    setQueue(q); setApps(a); setReminders(r); setContacts(c);
    setSelected(old => {
      if (!old) return null;
      const current = a.find(x => x.job_id === old.job_id) || null;
      return q.find(j => j.job_id === old.job_id) || { ...old, application: current,
        eligibility: current?.eligibility_details?.assessment || old.eligibility };
    });
  }, []);
  useEffect(() => { load().catch(e => setMessage(e.message)); }, [load]);
  const refreshDetail = async (row: Row) => {
    const pkgs = await request<Package[]>(`${BASE}/api/jobs/${row.job_id}/packages`);
    setPackages(pkgs);
    if (row.application) {
      const [d, h] = await Promise.all([request<Draft[]>(`${API}/applications/${row.application.id}/outreach`),
        request<History[]>(`${API}/applications/${row.application.id}/history`)]);
      setDrafts(d); setHistory(h);
    } else { setDrafts([]); setHistory([]); }
  };
  const select = async (row: Row) => {
    setSelected(row); setMessage(""); setUrl(row.application?.application_url || row.url);
    setPackageId(row.application?.package_id || 0); setCv(row.application?.preparation.cv_document_id || 0);
    setLetter(row.application?.preparation.cover_letter_document_id || 0);
    setQuestions(row.application?.preparation.questions || []); setFields(row.application?.preparation.verified_fields || {});
    setReviewed(false); setOfficial(false); setAcknowledge(false); setSubmitted(false); setConfirmation("");
    try { await refreshDetail(row); } catch (e) { setMessage((e as Error).message); }
  };
  const act = async (action: () => Promise<unknown>, success: string) => {
    setBusy(true); setMessage("");
    try { await action(); await load(); if (selected) await refreshDetail(selected); setMessage(success); }
    catch (e) { setMessage((e as Error).message); }
    finally { setBusy(false); }
  };
  const allRows: Row[] = view === "queue" ? queue : apps.map(a => queue.find(r => r.job_id === a.job_id) || ({
    job_id: a.job_id, company: a.job_company, title: a.job_title, location: a.job_location, country: a.country,
    url: a.application_url, match_score: a.match_score, sponsorship_status: a.sponsorship_status,
    eligibility: a.eligibility_details?.assessment || { overall_status: a.eligibility_status, checks: [], match_score: a.match_score, sponsorship_status: a.sponsorship_status }, application: a
  }));
  const rows = allRows.filter(r => (!country || r.country === country) && r.company.toLowerCase().includes(employer.toLowerCase()) &&
    (!status || r.application?.status === status) && (!eligibility || r.eligibility.overall_status === eligibility) &&
    (!sponsorship || r.sponsorship_status === sponsorship) && r.match_score >= minScore &&
    (!since || (r.application?.updated_at || "") >= since)).sort((a,b) => sort === "company" ? a.company.localeCompare(b.company) :
      sort === "date" ? (b.application?.updated_at || "").localeCompare(a.application?.updated_at || "") : b.match_score - a.match_score);
  const a = selected?.application, pkg = packages.find(p => p.id === packageId);
  const preparationSaved = !!a && a.package_id === packageId && a.preparation.cv_document_id === cv &&
    a.preparation.cover_letter_document_id === letter && a.application_url === url &&
    JSON.stringify(a.preparation.questions || []) === JSON.stringify(questions) &&
    JSON.stringify(a.preparation.verified_fields || {}) === JSON.stringify(fields);
  const openPortal = async () => {
    if (!a) return;
    // Open synchronously in the click handler to avoid popup blocking. Navigation follows approval validation.
    const win = window.open("about:blank", "_blank");
    if (win) win.opener = null;
    await act(async () => {
      try { await request(`${API}/applications/${a.id}/start`, "POST"); if (win) win.location.href = a.application_url; }
      catch (error) { win?.close(); throw error; }
    }, "Preparation started. Submit manually on the employer portal, then record confirmation here.");
  };

  return <div className="space-y-5">
    <div className="rounded-xl border border-indigo-800 bg-indigo-950/30 p-5">
      <h2 className="text-xl font-semibold">Application Control Center</h2>
      <p className="text-sm text-slate-300 mt-2">Review eligibility, select approved documents and prepare each application. Final submission stays with you.</p>
      <p className="text-xs text-amber-300 mt-2">Unknown sponsorship and work authorization require review. Scores measure fit, not interview probability.</p>
    </div>
    {message && <div role="status" className="rounded border border-amber-700 bg-slate-900 p-3 whitespace-pre-wrap">{message}</div>}
    <div className="flex gap-3"><button className={button} onClick={() => setView("queue")}>Suitable jobs queue ({queue.length})</button>
      <button className={secondary} onClick={() => setView("applications")}>All applications ({apps.length})</button>
      <button className={secondary} onClick={() => act(load, "Refreshed")}>Refresh</button></div>
    <div className="grid gap-3 md:grid-cols-4">
      <label className="text-xs">Country<select aria-label="Country" className={input} value={country} onChange={e => setCountry(e.target.value)}><option value="">All countries</option>{Array.from(new Set(allRows.map(r => r.country).filter(Boolean))).map(c => <option key={c}>{c}</option>)}</select></label>
      <label className="text-xs">Employer<input className={input} value={employer} onChange={e => setEmployer(e.target.value)} /></label>
      <label className="text-xs">Eligibility<select aria-label="Eligibility" className={input} value={eligibility} onChange={e => setEligibility(e.target.value)}><option value="">All</option>{Object.entries(labels).map(([v,l]) => <option key={v} value={v}>{l}</option>)}</select></label>
      <label className="text-xs">Stage<select aria-label="Stage" className={input} value={status} onChange={e => setStatus(e.target.value)}><option value="">All</option>{["shortlisted","documents_prepared","ready_for_review","in_progress","submitted","follow_up_due","interview_scheduled","rejected","offer_received","withdrawn"].map(v => <option key={v} value={v}>{pretty(v)}</option>)}</select></label>
      <label className="text-xs">Minimum score<input type="number" min={0} max={100} className={input} value={minScore} onChange={e => setMinScore(Number(e.target.value))} /></label>
      <label className="text-xs">Sponsorship<select aria-label="Sponsorship" className={input} value={sponsorship} onChange={e => setSponsorship(e.target.value)}><option value="">All</option>{["Confirmed","Not Supported","Unknown"].map(v => <option key={v}>{v}</option>)}</select></label>
      <label className="text-xs">Updated since<input type="date" className={input} value={since} onChange={e => setSince(e.target.value)} /></label>
      <label className="text-xs">Sort<select aria-label="Sort" className={input} value={sort} onChange={e => setSort(e.target.value)}><option value="score">Highest score</option><option value="company">Employer</option><option value="date">Most recently updated</option></select></label>
    </div>
    <div className="overflow-auto rounded border border-slate-700"><table className="w-full text-sm text-left"><thead className="bg-slate-900"><tr>{["Vacancy","Fit","Eligibility / visa","Preparation","Submission",""].map(h => <th key={h} className="p-3">{h}</th>)}</tr></thead>
      <tbody>{rows.map(r => <tr key={r.job_id} className="border-t border-slate-800"><td className="p-3"><strong>{r.title}</strong><p>{r.company} · {r.location}</p></td><td className="p-3">{r.match_score}/100</td><td className="p-3">{pretty(r.eligibility.overall_status)}<p className="text-slate-400">Sponsorship: {r.sponsorship_status}</p></td><td className="p-3">{r.application ? pretty(r.application.status) : "Not shortlisted"}<p className="text-slate-400">{r.application?.package_id ? "CV and letter selected" : "Documents needed"}</p></td><td className="p-3">{r.application?.date_submitted ? `User confirmed: ${r.application.confirmation_reference}` : "Not recorded"}</td><td className="p-3"><button className={secondary} disabled={busy} onClick={() => select(r)}>Review</button></td></tr>)}</tbody></table>
      {!rows.length && <p className="p-5 text-slate-400">No vacancies match these filters.</p>}</div>
    {selected && <section className="space-y-5 rounded-xl border border-slate-700 p-5">
      <div className="flex justify-between gap-3"><h3 className="text-lg font-semibold">{selected.title} · {selected.company}</h3><button onClick={() => setSelected(null)}>Close</button></div>
      <p>{selected.location} · {pretty(selected.eligibility.overall_status)}</p>
      <details open><summary className="cursor-pointer font-semibold">Eligibility evidence and unknowns</summary><div className="mt-3 space-y-2">{selected.eligibility.checks.map((c,i) => <div key={`${c.category}-${i}`} className="border-b border-slate-800 py-2 text-sm"><strong>{pretty(c.category)}: {pretty(c.status)}</strong>{c.is_mandatory && " · mandatory"}<p className="text-slate-400">{c.detail}</p>
        {a && !a.date_submitted && !["occupational_relevance","closing_date"].includes(c.category) && <div className="flex gap-2 mt-2"><button className={secondary} disabled={busy} onClick={() => { const evidence = window.prompt("Enter the verified evidence for this requirement (including source):"); if (evidence) act(() => request(`${API}/applications/${a.id}/eligibility-review`, "POST", { checks: [{ category:c.category, status:"met", evidence }] }), "Eligibility evidence saved; application approval reset."); }}>Record verified evidence</button><button className={secondary} disabled={busy} onClick={() => { const evidence = window.prompt("Explain the confirmed requirement you do not meet:"); if (evidence) act(() => request(`${API}/applications/${a.id}/eligibility-review`, "POST", { checks: [{category:c.category,status:"not_met",evidence}] }), "Eligibility updated."); }}>Record unmet requirement</button></div>}</div>)}</div></details>
      {!a ? <button className={button} disabled={busy} onClick={() => act(() => request(`${API}/applications`, "POST", { job_id:selected.job_id }), "Shortlisted. Review this vacancy again to prepare documents.")}>Shortlist vacancy</button> : <>
        <h4 className="font-semibold">1. Review profile and select documents</h4>
        <p className="text-sm text-amber-300">Check every employer, date, qualification and contact detail. Existing saved packages may contain older profile information.</p>
        <button className={button} onClick={() => onStudio(selected.job_id)}>Generate / review documents in Application Studio</button>
        <div className="grid md:grid-cols-3 gap-3"><label>Package<select aria-label="Package" className={input} value={packageId} onChange={e => {setPackageId(Number(e.target.value));setCv(0);setLetter(0);}}><option value={0}>Select approved package</option>{packages.map(p => <option key={p.id} value={p.id}>Package {p.id} · {p.status}</option>)}</select></label>
          <label>CV version<select aria-label="CV version" className={input} value={cv} onChange={e => setCv(Number(e.target.value))}><option value={0}>Select CV</option>{pkg?.documents.filter(d => d.doc_type.startsWith("cv_")).map(d => <option key={d.id} value={d.id}>{d.doc_type} v{d.version_number} · {d.is_approved ? "approved" : "draft"}</option>)}</select></label>
          <label>Cover-letter version<select aria-label="Cover-letter version" className={input} value={letter} onChange={e => setLetter(Number(e.target.value))}><option value={0}>Select cover letter</option>{pkg?.documents.filter(d => d.doc_type.startsWith("cover_letter_")).map(d => <option key={d.id} value={d.id}>{d.doc_type} v{d.version_number} · {d.is_approved ? "approved" : "draft"}</option>)}</select></label></div>
        <div className="flex gap-3">{pkg?.documents.filter(d => [cv,letter].includes(d.id)).map(d => <a key={d.id} className={secondary} href={`${BASE}/api/packages/${pkg.id}/download?doc_type=${d.doc_type}`} download>Download {d.doc_type}</a>)}</div>
        <label className="block">Employer application URL<input className={input} value={url} onChange={e => setUrl(e.target.value)} /></label>
        <label className="block"><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} /> I reviewed the candidate facts and selected documents.</label>
        <label className="block"><input type="checkbox" checked={official} onChange={e => setOfficial(e.target.checked)} /> I verified this application URL belongs to the employer or its authorized job platform.</label>
        <h4 className="font-semibold">2. Prepare verified fields and answers</h4><p className="text-sm text-slate-400">Only enter facts you can verify. Unknown answers stay blank; add mandatory questions from the employer form.</p>
        <div className="grid md:grid-cols-3 gap-3">{["name","email","phone","location","current_role","current_company"].map(key => <label key={key}>{pretty(key)}<input className={input} value={fields[key] || ""} onChange={e => setFields({...fields,[key]:e.target.value})} /></label>)}</div>
        {questions.map((q,i) => <div key={i} className="grid md:grid-cols-2 gap-3 border border-slate-700 p-3 rounded"><label>Question<input className={input} value={q.question} onChange={e => setQuestions(questions.map((x,j) => j===i ? {...x,question:e.target.value,verified:false} : x))} /></label><label>Answer<textarea className={input} value={q.answer} onChange={e => setQuestions(questions.map((x,j) => j===i ? {...x,answer:e.target.value,verified:false} : x))} /></label><label><input type="checkbox" checked={q.mandatory} onChange={e => setQuestions(questions.map((x,j) => j===i ? {...x,mandatory:e.target.checked} : x))} /> Mandatory</label><label><input type="checkbox" checked={q.verified} onChange={e => setQuestions(questions.map((x,j) => j===i ? {...x,verified:e.target.checked} : x))} /> Answer verified</label><button className={secondary} onClick={() => setQuestions(questions.filter((_,j) => i!==j))}>Remove question</button></div>)}
        <button className={secondary} onClick={() => setQuestions([...questions,{question:"",answer:"",mandatory:true,verified:false}])}>Add application question</button>
        <div><button className={button} disabled={busy || !cv || !letter || !reviewed || !official || !!a.date_submitted} onClick={() => act(() => request(`${API}/applications/${a.id}/prepare`, "PUT", {package_id:packageId,cv_document_id:cv,cover_letter_document_id:letter,application_url:url,questions,verified_fields:fields,profile_reviewed:reviewed,official_url_verified:official}), "Preparation saved; review and approve this version.")}>Save preparation</button></div>
        <h4 className="font-semibold">3. Approve this application preparation</h4>
        {!preparationSaved && <p className="text-amber-300 text-sm">Save the current document selection, fields and answers before approving.</p>}
        <label className="block"><input type="checkbox" checked={acknowledge} onChange={e => setAcknowledge(e.target.checked)} /> I reviewed unresolved eligibility information and will clarify it with the employer.</label>
        <label className="block">Approval notes<textarea className={input} value={notes} onChange={e => setNotes(e.target.value)} /></label>
        <div className="flex gap-3"><button className={button} disabled={busy || !preparationSaved || !!a.date_submitted} onClick={() => act(() => request(`${API}/applications/${a.id}/approve`, "POST", {acknowledge_unknowns:acknowledge,notes}), "Preparation approved. Document, profile or answer changes require fresh approval.")}>Approve preparation</button><button className={secondary} disabled={busy || !a.user_approved || !!a.date_submitted} onClick={openPortal}>Open portal and begin</button></div>
        <p className="text-sm text-slate-400">Sign in manually, copy verified fields and upload the selected files. Handle verification yourself. Review every answer and click Submit on the portal yourself. Opening a portal does not record submission.</p>
        <h4 className="font-semibold">4. Record manual submission</h4>
        <label className="block">Employer confirmation number or confirmation-email reference<input className={input} value={confirmation} onChange={e => setConfirmation(e.target.value)} /></label>
        <label className="block"><input type="checkbox" checked={submitted} onChange={e => setSubmitted(e.target.checked)} /> I submitted this application manually and received confirmation.</label>
        <label className="block"><input type="checkbox" checked={followUp} onChange={e => setFollowUp(e.target.checked)} /> Remind me to follow up after <input type="number" min={1} max={365} className="bg-slate-900 border border-slate-600 rounded p-1 w-16" value={days} onChange={e => setDays(Number(e.target.value))} /> days</label>
        <button className={button} disabled={busy || !submitted || !!a.date_submitted} onClick={() => act(() => request(`${API}/applications/${a.id}/record-submission`, "POST", {confirmation_reference:confirmation,manually_submitted:submitted,follow_up_enabled:followUp,follow_up_days:days}), "Manual submission recorded with your confirmation.")}>Record confirmed submission</button>
        <div className="flex gap-3"><select aria-label="New application stage" className={input} value={stage} onChange={e => setStage(e.target.value)}>{["follow_up_due","interview_scheduled","rejected","offer_received","withdrawn"].map(s => <option key={s} value={s}>{pretty(s)}</option>)}</select><button className={secondary} disabled={busy} onClick={() => act(() => request(`${API}/applications/${a.id}/status`, "PUT", {status:stage,notes}), "Application stage updated.")}>Update stage</button></div>
        <h4 className="font-semibold">Recruiter outreach — drafts only</h4>
        <div className="grid md:grid-cols-3 gap-3"><label>Contact name<input className={input} value={contactName} onChange={e => setContactName(e.target.value)} /></label><label>Company<input className={input} value={contactCompany} onChange={e => setContactCompany(e.target.value)} /></label><label>Email (optional)<input className={input} value={contactEmail} onChange={e => setContactEmail(e.target.value)} /></label></div>
        <button className={secondary} disabled={busy || !contactName.trim()} onClick={() => act(() => request(`${API}/contacts`, "POST", {name:contactName,company:contactCompany,email:contactEmail}), "Contact saved from the details you entered.")}>Save contact</button>
        <div className="flex gap-3"><select aria-label="Recruiter contact" className={input} value={contactId} onChange={e => setContactId(Number(e.target.value))}><option value={0}>No named contact</option>{contacts.map(c => <option key={c.id} value={c.id}>{c.name} · {c.company}</option>)}</select><select aria-label="Outreach type" className={input} value={kind} onChange={e => setKind(e.target.value)}>{["recruiter","hiring_manager","talent_acquisition","referral","follow_up"].map(k => <option key={k} value={k}>{pretty(k)}</option>)}</select><select aria-label="Outreach channel" className={input} value={channel} onChange={e => setChannel(e.target.value)}><option value="linkedin">LinkedIn</option><option value="email">Email</option></select><button className={button} disabled={busy} onClick={() => act(() => request(`${API}/applications/${a.id}/outreach`, "POST", {contact_id:contactId || null,kind,channel}), "Editable draft created. Send manually after review.")}>Draft message</button></div>
        {drafts.map(d => <div key={d.id} className="space-y-2 border border-slate-700 rounded p-3"><input aria-label="Message subject" disabled={d.is_sent} className={input} value={d.subject} onChange={e => setDrafts(drafts.map(x => x.id===d.id ? {...x,subject:e.target.value,is_approved:false} : x))} /><textarea aria-label="Message body" disabled={d.is_sent} rows={5} className={input} value={d.message_body} onChange={e => setDrafts(drafts.map(x => x.id===d.id ? {...x,message_body:e.target.value,is_approved:false} : x))} /><div className="flex gap-3"><button className={secondary} disabled={busy || d.is_sent} onClick={() => act(() => request(`${API}/outreach/${d.id}`, "PUT", {message_body:d.message_body,subject:d.subject}), "Draft saved. Approve the saved wording separately.")}>Save edits</button><button className={secondary} disabled={busy || d.is_sent} onClick={() => act(() => request(`${API}/outreach/${d.id}`, "PUT", {message_body:d.message_body,subject:d.subject,approved:true}), "Draft reviewed. No message sent.")}>Approve wording</button><button className={secondary} disabled={busy || !d.is_approved || d.is_sent} onClick={() => { if (window.confirm("Have you sent this exact message manually?")) act(() => request(`${API}/outreach/${d.id}`, "PUT", {message_body:d.message_body,subject:d.subject,approved:true,manually_sent:true}), "Manual outreach recorded."); }}>Record manually sent</button></div></div>)}
        <h4 className="font-semibold">Follow-up schedule</h4><div className="flex gap-3"><input aria-label="Reminder title" className={input} placeholder="Reminder title" value={reminderTitle} onChange={e => setReminderTitle(e.target.value)} /><input aria-label="Reminder date" type="datetime-local" className={input} value={due} onChange={e => setDue(e.target.value)} /><button className={secondary} disabled={busy || !due || !reminderTitle} onClick={() => act(() => request(`${API}/applications/${a.id}/reminders`, "POST", {title:reminderTitle,due_date:new Date(due).toISOString()}), "Reminder scheduled.")}>Add reminder</button></div>
        <details><summary>Application history ({history.length})</summary>{history.map(h => <div key={h.id} className="p-2 text-sm border-b border-slate-800"><strong>{pretty(h.action)}</strong> · {h.created_at}<pre className="whitespace-pre-wrap text-xs text-slate-400">{JSON.stringify(h.details,null,2)}</pre></div>)}</details>
      </>}
    </section>}
    <section className="rounded-xl border border-slate-700 p-5"><h3 className="font-semibold mb-3">Local reminders</h3><p className="text-sm text-slate-400 mb-3">Windows notifications require the included reminder task setup. No recruiter is contacted.</p>
      {reminders.filter(r => !r.is_completed && !r.is_dismissed).map(r => <div key={r.id} className="flex flex-wrap gap-3 items-center border-t border-slate-800 p-3"><span className="flex-1">{r.title} · {new Date(r.due_date+"Z").toLocaleString()}</span><button className={secondary} onClick={() => act(() => request(`${API}/reminders/${r.id}`, "PUT", {is_completed:true}), "Reminder completed.")}>Complete</button><button className={secondary} onClick={() => act(() => request(`${API}/reminders/${r.id}`, "PUT", {is_dismissed:true}), "Reminder disabled.")}>Disable</button><button className={secondary} onClick={() => {const next = window.prompt("New reminder date and time, e.g. 2026-11-20T09:00");if (next && !Number.isNaN(Date.parse(next))) act(() => request(`${API}/reminders/${r.id}`, "PUT", {due_date:new Date(next).toISOString()}), "Reminder rescheduled.");}}>Reschedule</button></div>)}
      {!reminders.some(r => !r.is_completed && !r.is_dismissed) && <p className="text-slate-400">No pending reminders.</p>}
    </section>
  </div>;
}
