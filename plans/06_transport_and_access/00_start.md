---
status: draft
---

# Transport and access

## Where this came from

Asked on 2026-09-19, while the viewer was being read on a phone over Tailscale: how does the Kobo
authenticate to the host, and how does it connect, given the Kobo is not on the tailnet.

It is a folder rather than a line in an existing open question because the honest answer today is
that there is no authentication at all, and the first thing that widens the listener past loopback
turns that from a non-issue into the main issue. The nearest existing homes for it were Q4 in
[`../02_kobo/00_start.md`](../02_kobo/00_start.md), which asks about transport and not about trust,
and D8 in [`../01_implementation/tracking.md`](../01_implementation/tracking.md), which answered the
question for a Kindle by assuming Tailscale on the device. That assumption is the one being removed.

## What is true today

Checked rather than recalled, on 2026-09-19.

- `KLD2` has no handshake, no credential and no acknowledgement. `src/klide/host.py` binds, calls
  `listen(1)`, calls `accept()`, and starts sending frames to whatever connected. See "What is not
  here yet" in [`../../docs/protocol.md`](../../docs/protocol.md).
- The host binds `127.0.0.1` by default as of 2026-09-19. Widening it is now something a command
  line asks for.
- The connection is opened by the device, outward to the host, decided in
  [`../02_kobo/01_ui_ux.md`](../02_kobo/01_ui_ux.md). So the host has to be listening somewhere the
  device can reach, which by definition is not loopback.
- This box runs no OpenSSH server. Only `tailscaled`, on `100.126.229.25`, with the LAN address
  `192.168.0.157`. Anything that wants to reach in over plain SSH has nothing to reach.
- The viewer is a second client of the same protocol and is written against the specification rather
  than against klide's code, deliberately (V3 in
  [`../04_klide_app/05_viewer.md`](../04_klide_app/05_viewer.md)). Anything added to `KLD2` costs two
  implementations, one of them in Lua.

## Two questions that keep getting merged

**Reachability.** Whether a packet from the device can arrive at the host at all. A routing and NAT
question, with no security content.

**Authorization.** Who may drive and, more to the point, who may read, once a packet can arrive. A
credential question, with no routing content.

They have different answers in every case below, and a solution to one is regularly mistaken for a
solution to the other. Tailscale happens to answer both, which is why it hides the distinction.

## What is exposed, precisely

Not the buttons. The frames.

A frame is the user's live Claude Code transcript, rendered as pixels, in a format documented in this
repo. Anything that can open the socket receives every frame the host sends, including whatever was
on screen when it connected. Paging around someone else's session is the second-order problem; the
first is that the session is legible to the connection.

Two details make it slightly worse than it sounds. `listen(1)` serves one client, so whoever
connects first holds the session. And klide is read-only toward Claude (D11), which bounds the damage
to disclosure: nothing on this wire can write to the session it is watching.

## Case A, same network

The Kobo on the house wifi, the host on the same LAN. Host binds `192.168.0.157`, device dials it.

Reachability is free. Authorization is absent: every device on that network can connect, and on a
network with guests, a television and whatever else, "every device" is not a short list. Client
isolation on a guest SSID would prevent it, which is a property of the router and not of klide.

This is the cheapest path to the only question that actually matters first, which is whether a Lua
client can speak `KLD2` at all. For that purpose it is fine, bound for the length of the spike and
taken down after. It is not fine as the routine path.

## Case B, a different wifi entirely

The Kobo on a network the host is not on: a cafe, a hotel, a train, an office, a phone hotspot.

Reachability stops being free and becomes the whole problem. The device dials outward, the host sits
behind a home router with no public address and no forwarded port, and there is no route. Nothing
connects, and no amount of authentication design changes that. Authorization is a question that only
arises after a path exists.

Authorization also changes character once a path exists, and this is the part worth being careful
about. On the house LAN the other devices belong to the user. On a foreign network they do not, and
the operator of that network sees the traffic. A credential proves who is connecting. It does nothing
about who is reading. So a token that would be proportionate in case A is not sufficient here: case B
requires an encrypted transport, whatever else it also has.

The ways to bridge it, with what each costs:

**Tailscale on the Kobo.** The device joins the tailnet and `100.126.229.25:5000` works from any
network, exactly as the phone reaches the viewer today. Reachability and confidentiality in one move,
with identity as a side effect and no protocol change at all. Every cost is on the device: an ARM
build, `/dev/net/tun` or the userspace fallback, a daemon running alongside KOReader and drawing
power, an install and a removal under the borrowed-device rules, and a login on a device with no
usable browser. That last one has an answer, `tailscale up --authkey` with an ephemeral key, which
puts a revocation step into the removal plan. None of it is verified on this firmware and none of it
can be verified from here.

It also survives hostile networks better than the alternatives, because when direct UDP is blocked it
falls back to a relay over 443, which is the port such networks leave open.

**Port forward and dynamic DNS.** Open the home router to the internet on 5000. This publishes an
unauthenticated, unencrypted service that streams a transcript to anyone who scans the port, and
scanning is continuous and automated. Rejected, and it stays rejected even after a credential exists,
because the first version of any handshake is the one being attacked.

**A relay with a public address.** A small machine with a real address that both ends dial outward
to, joining the two connections. It converts the problem into "who may connect to the relay", which
is the same authorization question relocated to a machine that can be configured, and TLS comes free
if the relay speaks it. Costs a machine, a name, a second hop on every frame, and a third party that
now sees the traffic unless the ends encrypt to each other.

**Cloudflare Tunnel.** Already on this box for HTTP. It can carry arbitrary TCP, but the far end
needs `cloudflared access tcp` running as a local proxy, which is a Go binary on the Kobo. That is
the same install cost as Tailscale with less of the benefit, so it is only interesting if cloudflared
runs on that device and tailscaled does not. Anything under `/etc/cloudflared/` here is root-only and
off limits, so a tunnel for this would be a separately planned change rather than a reuse.

**Tether to the phone.** The phone is already on the tailnet. If the Kobo joins the phone's hotspot,
the question becomes whether the phone will route it into the tailnet, which needs subnet routing or
an exit node on a mobile client. Installs nothing on the Kobo, which is why it is worth an hour. The
mobile clients are the weak part and it is unverified.

Two practical blockers apply to all of them and are easy to forget until standing in a hotel.
A captive portal wants a browser to accept terms before any packet leaves the device, and a Kobo is a
poor place to meet that requirement. And a network that allows only 80 and 443 outbound kills a raw
service on 5000, which is an argument for whichever tunnel is chosen being able to run over 443.

## Provisioning is physical

The client is installed by plugging the device into a computer. A KOReader plugin is files under
`.adds/koreader/plugins/`, copied over USB mass storage, on one device, by the person who owns both
ends. This was confirmed as acceptable on 2026-09-19 rather than assumed.

That changes what is reasonable to build, because the usual objection to a secret inside a client
does not apply. That objection is about an artifact handed to thousands of strangers: the secret is
public the moment one of them unzips it, and rotating it means shipping an update to an install base
that may never take it. There is no store here, no update channel, no install base and no strangers.
One device, provisioned by hand.

What the USB step buys:

- A per-device key written into the install at provisioning time, with the matching value on the
  host. No key exchange over the network, no pairing gesture, no window during which an unknown
  client is trusted because it happened to be first.
- Rotation is plugging the cable in again.
- Removal is deleting a file, which the borrowed-device rules require regardless, plus dropping the
  value on the host.
- Nothing has to be typed on an e-ink keyboard, which is the other reason a pairing flow would be
  unpleasant here.

What it does not buy, kept separate because the two get merged:

- It is not encryption. A provisioned key proves who is connecting and leaves the frames readable to
  anything on the path, unless the key is used to encrypt rather than only to authenticate.
- The key sits on the device in the clear, because a Kobo has nowhere to hide it. It is a revocable
  credential rather than a secret, and it should be designed as one: one key per device, invalidated
  on the host in a second, which also covers the device going back with the file still on it.

## Decisions

* **TD1. Reachability and authorization are answered separately.** Every option below is graded on
  both, and an option that solves one is not recorded as solving the other. Tailscale solving both at
  once is the reason this rule is written down.
* **TD2. What is protected is the frames.** The threat is disclosure of the transcript, not
  mischievous page turns. Any proposal is judged on who can read, first.
* **TD3. Loopback is the default and every widening is explicit.** Shipped 2026-09-19. Until this
  folder closes, a wider bind is a deliberate command for the length of a spike, taken down after.
* **TD4. The client is provisioned over USB, on one device, by hand.** Accepted by the user on
  2026-09-19. A per-device key written at install time is therefore a legitimate design here, and the
  reflex against embedding credentials in a client does not transfer, because it is a rule about
  public distribution and there is none.
* **TD5. A credential authenticates and does not encrypt.** Any path across a network the user does
  not control requires an encrypted transport regardless of what `KLD2` carries. This is what makes
  case B a different design from case A rather than a longer version of it.
* **TD6. Nothing is added to `KLD2` before the device facts are known.** Same reasoning as D1 in
  [`../04_klide_app/06_device_client.md`](../04_klide_app/06_device_client.md): a protocol change the
  Lua client cannot implement is worse than no protocol change, and here it would also break the
  viewer, which is the second implementation.

## Open questions

Numbered `T` for this folder, continuing across batches.

- T1: Does `tailscaled` run usefully on this Kobo, on 4.38.23552. A yes makes most of this folder
  unnecessary and case B free; a no is what forces the rest of it.
  a. test it early, before any protocol work
  b. assume no and design the credential path first
  Recommended: a. It is the single fact with the most leverage, it needs the device rather than
  reasoning, and it is cheap once the device is in hand.
  NEW_ANS:
- T2: Is case B a requirement or a convenience. A Kobo that never leaves the house is a much smaller
  problem than one carried to a cafe, and the two justify different amounts of work.
  NEW_ANS:
- T3: If `KLD2` gains a handshake, what shape. Constraints already known: readable with
  `string.byte` arithmetic, fixed length, compared in constant time, and implemented twice because
  the viewer speaks the same protocol. A version bump or a new message type is the sub-question.
  NEW_ANS:
- T4: What can encrypt on the device, if the answer to T1 is no and case B is wanted. Whether
  KOReader's Lua has a usable TLS binding is a fact about that firmware, to be found on the device
  and not reasoned out from here. Unknown.
  NEW_ANS:
- T5: Where the host keeps the key and how it is revoked. A file, an environment variable, a flag,
  and what happens to a connection presenting an old one.
  NEW_ANS:
- T6: Whether the viewer presents the same credential or is exempted because it is local. Exempting
  it keeps one implementation simple and makes the loopback bind the thing doing the work, which is
  an argument for the exemption and against it at the same time.
  NEW_ANS:
