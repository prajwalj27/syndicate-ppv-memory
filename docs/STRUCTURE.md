ppv-memory/
├── PLAN.md                          # your implementation plan (already have this)
├── README.md                        # final submission doc — what it does, how to run, track, etc.
├── requirements.txt                 # Python dependencies
├── .gitignore
│
├── data/
│   ├── ppv_memory.db                 # SQLite DB (already created — Step 1)
│   ├── invoices/                     # synthetic invoice text files (already created — Step 1)
│   │   ├── INV-1001.txt
│   │   ├── INV-1002.txt
│   │   ├── INV-1003.txt
│   │   ├── INV-1004.txt
│   │   └── INV-1005.txt
│   └── SCENARIO_KEY.md               # your ground-truth answer key (copy in from earlier)
│
├── scripts/
│   └── generate_data.py              # Step 1 (already done)
│
├── src/
│   ├── extraction.py                 # Step 2: invoice text -> structured data
│   ├── decision.py                   # Step 3: variance calc + auto-approve/flag logic
│   ├── memory.py                     # Step 4: resolution read/write against the resolutions table
│   ├── pipeline.py                   # ties extraction -> decision -> memory together end-to-end
│   └── db.py                         # shared SQLite connection/query helpers
│
├── app/
│   └── review_queue.py               # Step 5: Streamlit (or Flask) review UI
│
├── eval/
│   └── mini_eval.py                  # Step 6: with/without-memory before/after comparison
│
└── tests/                            # optional but nice to have if time allows
    └── test_pipeline.py