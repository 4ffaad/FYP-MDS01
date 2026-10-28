# MDS01 final report package

This folder contains the assessment-structured report source, its draft RTM,
the representative source-code appendix, and the import-ready Word document.
The report describes the implementation and verification evidence available in
the repository; it is not a clinical validation report.

## Files

- [Final report source](final-report.md) — editable Markdown master.
- [Final report DOCX](MDS01_Final_Project_Report.docx) — formatted copy for
  Google Docs import while no connected shared document session is available.
- [Draft RTM](rtm.md) — status and evidence matrix requiring team/supervisor
  review.
- [Representative source sample](source-code-sample.md) — excerpts from the
  encrypted storage service.
- [Evidence screenshots](assets/) — synthetic UI-test captures only; B2 is a
  focused crop showing the score timeline and Grad-CAM evidence panel.

The four editable Draw.io diagrams and their visual previews are in
[`../diagrams/README.md`](../diagrams/README.md). Do not replace these sources
with screenshots; update the JSON specification, rebuild the `.drawio` file,
and refresh the preview together.

## Submission checks still requiring the team

1. Confirm the authorship leadership statement on the cover sheet and verify
   that every team member approves it.
2. Review and sign off the draft RTM with the supervisor.
3. Confirm the final word count after any group edits.
4. Add the actual approved end-product screenshots if the team has a safe,
   non-identifying capture from the final demo. The included screenshots use
   synthetic browser-test data.
5. Apply the unit's GenAI disclosure and Google Docs edit-history requirements.


## Regenerate the Word file

The Markdown source is authoritative. With `uv` installed, create a local
throwaway Python environment and build the DOCX:

```sh
uv venv --python 3.12 /tmp/mds01-report-env
uv pip install --python /tmp/mds01-report-env/bin/python python-docx lxml
/tmp/mds01-report-env/bin/python docs/final-report/build_docx.py
```

For Google Docs import, run the Documents skill's title sanitizer on the
generated DOCX. The sanitizer is part of the local workstation skill and is not
a repository dependency. The Word file includes the four diagrams, the draft
RTM, synthetic screenshots, and the source-code appendix. The shared Google
Doc can be updated once its document session is connected.
