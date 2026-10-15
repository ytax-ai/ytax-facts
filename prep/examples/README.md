# Examples

Two folders of synthetic input for the local page: `forms/`, one example of each tax form the
page can read, and `profiles/`, whole demo households whose documents add up to a return.

## Example forms

`forms/` holds one example PDF for each tax form the local page can read:

| file | form |
|---|---|
| `w-2.pdf` | Form W-2 |
| `w-2g.pdf` | Form W-2G |
| `1099-int.pdf` | Form 1099-INT |
| `1099-div.pdf` | Form 1099-DIV |
| `1099-b.pdf` | Form 1099-B |
| `1099-oid.pdf` | Form 1099-OID |
| `1099-r.pdf` | Form 1099-R |
| `1099-misc.pdf` | Form 1099-MISC |
| `1099-g.pdf` | Form 1099-G |
| `1099-sa.pdf` | Form 1099-SA |
| `k1-1065.pdf` | Schedule K-1 (Form 1065) |
| `k1-1120s.pdf` | Schedule K-1 (Form 1120-S) |
| `k1-1041.pdf` | Schedule K-1 (Form 1041) |

**Every document here is synthetic.** None of them is a real tax document or comes from a real
return. Each page is marked `SYNTHETIC — NOT A REAL TAX DOCUMENT` across the middle, at the top and
at the bottom. The person named on them is made up, and the SSN printed on them starts with 900,
which is never issued to anyone. The payers, employers and entities are made up too.

Put any of these files on the page to see how a document is read. `forms/expected.json` lists, for
each file, the form it is read as and every figure the page takes from it (in cents).

On the 1099-B, boxes 1d, 1e, 2 and 3 are left blank: the page cannot find those boxes on a page yet,
so it asks for them.

## Demo profiles

`profiles/<profile>/input/` holds one synthetic household each:

- the household's tax documents as PDFs (W-2s, 1099s, K-1s and the others the page reads), the
  files to give the page;
- `interview.md`, the household's story and the answers to the questions the documents
  do not answer;
- `facts.json`, the same household as calculation-engine facts, which the demo runner uses to
  answer the page's questions and to check the finished return line by line.

Every profile is synthetic: made-up people, payers and amounts, with identifiers that are never
issued. Profiles whose name starts with `profile-ats-` or `profile-df-` restate published IRS test
scenarios; their identifiers are the IRS's own test identifiers as printed.

To open the page on one profile's documents:

```
YTAX_ENGINE_HOME=<engine home> collector/.venv/bin/python scripts/demo_intake.py --profile profile-C
```

`--profile all` puts every profile's documents on the page, one folder each; `--profile examples`
puts the example forms there instead.
