# transport and access tracking

How a client reaches the klide host, and how the host decides whether to talk to it. Opened because
the Kobo is not on the tailnet and `KLD2` has no authentication, so the first bind past loopback
turns a non-issue into the main one. Analysis and decisions in [`00_start.md`](00_start.md).

The device work this depends on is in [`../02_kobo/00_start.md`](../02_kobo/00_start.md); the client
that will use it is [`../04_klide_app/06_device_client.md`](../04_klide_app/06_device_client.md).

## Key decisions

- Reachability and authorization are answered separately, and an option solving one is not recorded
  as solving the other (TD1).
- What is protected is the frames, which carry the transcript, rather than the button presses (TD2).
- Loopback is the host's default bind; every widening is deliberate and lasts as long as a spike (TD3).
- The client is provisioned over USB on one device, so a per-device key at install time is a
  legitimate design and the rule against embedding credentials in a distributed app does not apply (TD4).
- A credential authenticates and does not encrypt, so a foreign network needs an encrypted transport
  whatever `KLD2` carries (TD5).
- Nothing is added to `KLD2` before the device facts are known, because a change the Lua client
  cannot implement is worse than no change, and it would cost the viewer too (TD6).

## Phases

| #  | Phase                 | Plan                                          | Status |
| -- | --------------------- | --------------------------------------------- | ------ |
| 1  | Device facts          | [`01_device_facts.md`](01_device_facts.md)    | draft |
| 2  | Same network          | [`02_same_network.md`](02_same_network.md)    | draft |
| 3  | A credential on the wire | [`03_credential.md`](03_credential.md)     | draft |
| 4  | Off the home network  | [`04_off_network.md`](04_off_network.md)      | draft |

Status values: draft / planned / in progress / done / superseded / discarded.

Every phase is draft because phase 1 is a spike on a device nobody has yet, and phases 3 and 4 are
shaped by what it finds. T1 alone can make phase 3 unnecessary and phase 4 free.

## Log

Append-only. Newest at the bottom.

- 2026-09-19 : opened, after the viewer was read from a phone over Tailscale and the same question
  was asked about the Kobo, which is not on the tailnet. Established by reading the code rather than
  the docs that `src/klide/host.py` accepts a connection and sends frames with no handshake of any
  kind, and by checking the listeners that this box runs no OpenSSH server, only `tailscaled`. Split
  the question into reachability and authorization, which Tailscale answers together and nothing else
  does. Named what is exposed, which is the transcript in the frames rather than the button presses.
  Analysed the case where the Kobo is on a foreign network: no route at all until something bridges
  it, and a credential stops being sufficient because the network operator can read what a credential
  does not encrypt. Recorded that provisioning is physical over USB, confirmed by the user the same
  day, which makes a per-device key written at install time reasonable here for the reason it is
  unreasonable in a publicly distributed app. Six decisions TD1-TD6, six questions T1-T6, four draft
  phases. The loopback default shipped the same day in `8041263`
