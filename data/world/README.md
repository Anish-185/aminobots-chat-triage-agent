Synthetic world (SPEC §7, §8), CC BY 4.0:

- `roster.yaml` — the only source of identity (A5): 3 partners, 6 outlets, 15 contacts with roles
  owner / manager / staff / accounts / aminobots_staff. Includes a shared phone (c08/c09), two
  Sureshes (c02/c06), an owner with 2 outlets (c01), accounts contacts, a delegate (c12 for c11)
  and two Aminobots staff.
- `contacts.yaml` — names saved on the exporting phone (display name → phone). Two saved names
  point to numbers that are not in the roster, to exercise name-only matches.

Every phone is `+91 55550 100NN` and fails `phonenumbers.is_valid_number()`
(`tests/test_synthetic_phones.py`).
