# Native manual-entry milestone

Prepared November 6, 2026. Implementation base: `afb5a5bf923a7fd45d8bd8d6c716f2b115d569ae` on `R-Mijo/SlipSavvy`. GitHub main, open issues and open pull requests were inspected before work; main matched the handoff and no open work was found. Other products, final names, licenses and Sites are outside this change.

## Deliverable

`mobile/App.tsx` supplies the missing native screen: enter a selection → review its exact fields → confirm → check single-selection payout scenarios. Independent combinations require explicit opt-in. `mobile/src/review.ts` handles reviewed manual entries and bounded replacement. `mobile/src/math.ts` reuses the earlier exact-fraction scaffold. No Python engine behavior is changed.

The first use case is manual pregame win-or-lose selections for separate games. The calculator is sport-agnostic because it consumes entered odds, not sports data. It supplies no forecasts or licensed feed and should not be marketed as a validated edge. The existing Apache-2.0 license is retained.

## Verification

The accompanying pull request records actual check outcomes and its exact head commit. Required checks for this milestone:

1. TypeScript compilation.
2. Exact arithmetic, invalid input, missing estimates, same-event exclusion, capacity, edit/replace and probability-boundary tests.
3. Expo exports for iOS, Android and web.
4. DOM interactions against the exported web application: required fields, review/confirm/edit/cancel, source labels, calculation invalidation, independence toggle, removal and education navigation.

DOM interactions do not test native keyboard behavior, screen readers, layout, Hermes runtime execution or a physical device. No native binary is signed, installed or submitted. Tests about candidate-text parsing only cover an unused utility, not OCR.

## Next practical milestone

Get this exact app commit running in compatible development builds on one physical iPhone and one Android phone. Exercise a small real-use script: enter a quoted price, catch a sign error in review, correct it, compare a single with two selections, explain gross versus profit, edit the stake and verify old results disappear. Check safe areas, keyboard access to negative odds, large text, VoiceOver/TalkBack and reload behavior. Record device/OS, commit, failures and fixes in GitHub. This is a device usability gate, not a request to activate paid services.

After that, add a licensed, timestamped source adapter for one sport/use case and a measured trial of user value. If a forecast is added, evaluate calibration separately before charging for claims about predictive performance. Keep screenshots as explicit user-reviewed suggestions, never automatically accepted odds.

## Paid release decisions still open

Checked against primary platform sources on November 6, 2026:

- [Apple App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) §3.1.1 generally routes digital feature unlocks through in-app purchase, with regional provisions; §3.1.2 requires ongoing value for subscriptions. §5.3.4 applies licensing, location restrictions and free download requirements to apps offering real-money gaming. This calculator's eventual classification is unconfirmed; it is not permission to run wagering or a guarantee of acceptance.
- [Google Play real-money gambling policy](https://support.google.com/googleplay/android-developer/answer/9877032?hl=en) distinguishes licensed gambling apps from other apps and sets free-download/no-Play-Billing rules for licensed gambling apps. Its express prohibition on gambling companion functionality is in the section about apps carrying gambling ads. Do not quote that section as a blanket ban on all standalone calculators. Avoid gambling ads, affiliate calls to wager and bookmaker navigation in this preview. Final classification and eligibility remain to be resolved for the actual release scope and countries.
- [Expo SDK reference](https://docs.expo.dev/versions/latest/) lists SDK 58 with React Native 0.88, React 19.3 and Node 22.13 or newer. This project pins the compatible 58/0.88/19.3 family and uses Node 24 for checks. [Expo Go availability](https://docs.expo.dev/troubleshooting/expo-go-version-mismatch/) is separate from SDK support; use a compatible development build for native testing.

Inference: finish device testing and platform classification before selecting a purchase implementation. Neither $0.49/month nor $5.88/year is an approved plan. Provider commercial rights, real operating costs, store price points/fees, refund/restore flows, paid ongoing value, privacy, age rating and support must be settled before enabling billing. No store accounts, charges, subscriptions or provider purchases were created.

## Collaboration with Gemini Argon

No Gemini findings or branch were supplied in this continuation, and no cross-chat sync is assumed. Use the pull request and its exact commit as the shared record. A review should identify the commit, file/line, reproduction input, expected and observed behavior, and command/output or device evidence. Independently reproduce a concrete finding before agreeing or making a fix. Inspect both current main and the proposed diff before overlapping edits; preserve remote changes. Add follow-up verification tied to the fix commit. Do not imply that Gemini reviewed this milestone until an actual review is available.
