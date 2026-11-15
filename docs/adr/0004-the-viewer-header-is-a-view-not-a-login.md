# 4. The viewer header shapes a view; it is not a login

Date: 15 November 2026. Status: accepted for the demo.

## Context

The mentors asked for one thing firmly: the crew medical officer sees every record, and each crew member sees their own. A sign-in system was out of reach for the weekend, and the demo holds only simulated data.

## Decision

The console names who is looking in the `X-LightTime-Viewer` header (or `?viewer=`), and the ship shapes its answers by it (`base_station/access.py`): with no header or with the crew medical officer's id, every record; with any other crew id, that person's own record, name cards for the rest, and a short notice of someone else's SOS.

## What follows from this

- The rule is in one file and is tested (`tests/test_access.py`), so a real sign-in can replace the header without changing what each role sees.
- It proves nothing. Anyone can send any id, and leaving the header out gives every record. The write routes, reset, the story, the dial and every Earth route ignore it. The console does not send the header yet, so its screens get the medical station's view.
- Every document calls these role-based views, never a login or access control, and [security and privacy](../tech/security-privacy.md) lists what is not protected.
- A real deployment would tie the role to a sign-in, add an emergency unlock for whoever helps during an open SOS, and log who read which record. An archived draft (`docs/specs/2026-11-15-secure-backend-design.md`) sketches this; nothing in it is built.
