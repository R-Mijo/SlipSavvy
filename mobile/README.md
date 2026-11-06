# SlipSavvy phone preview

First working native input/review milestone for iPhone and Android. The same React Native interface also exports to web for automated interaction checks. This is a development preview, not a store release or a prediction service.

For standalone installation on real phones, use [PHONE_TESTING.md](PHONE_TESTING.md) and the included `preview` build profile in `eas.json`. These builds include the app code and do not need a development server or Expo Go after installation. An Expo project and platform signing setup are still required; no installable build is supplied yet.

## Run

Node 24 LTS and npm are required. From `mobile/`:

```sh
npm ci
npm run check
npm test
npm run export
node tests/ui.cjs
npm start
```

Use a development client compatible with Expo SDK 58. Follow the current [Expo development-build instructions](https://docs.expo.dev/develop/development-builds/introduction/); do not assume the iPhone Expo Go app supports this SDK. Local native builds use `npm run android` with the Android toolchain, or `npm run ios` on macOS with Xcode. No account, cloud build, payment, signing or store upload is performed by the checks above. `expo export` compiles platform bundles; it does not produce signed APK/AAB/IPA files or run the app on a phone.

## What works

- Enter a selection, game and American odds. Source name, reference URL and the user's estimated chance are optional.
- Review the entered fields before confirming. Editing returns to the entry and review steps; it replaces the existing selection only after confirmation.
- Keep up to eight reviewed selections in memory. Remove a selection or edit stake/assumptions and previous calculations disappear immediately.
- Calculate exact fractional single-selection payouts, gross return, net profit and the break-even price threshold. Estimates never default to price-implied probabilities.
- Explicitly opt into independent combinations of two or three selections. Same-game combinations are excluded using normalized user-entered event names. Different names are not proof of different games or independence. Combined prices are hypothetical, not sportsbook quotes.
- Show assumed chance and expected net only when all selections in that scenario have a user-supplied probability. These are model scenarios, not calibrated confidence scores or recommendations.
- Learn odds, combined probabilities, gross versus net, model limits and affordable use in plain language.

The dark interface uses lime accents, safe-area insets, keyboard avoidance, named inputs, accessible buttons and a separate review step. These are implementation features; physical device accessibility and layout verification remain pending.

## Data and limits

The entry timestamp records when the user confirmed the selection. It does **not** claim that a provider checked the odds at that time. Source URLs are reference text and are not fetched or opened. Entries exist only in app memory and disappear after reload. There is no telemetry, persistence, sign-in, remote API, billing or wager placement in application code. Dependency, development-server and operating-system behavior must be included in the later release privacy audit.

This slice deliberately excludes screenshot access/OCR, live odds and injury feeds, weather, simulations, same-game modeling, pushes/voids/promotions, stake recommendations and purchase entitlements. `src/math.ts` retains previously written candidate-text/import helpers as unexposed utilities; they are not screenshot recognition or an import feature. The Python package remains the full scenario engine.

## Verification and next gates

See [the mobile milestone record](../docs/MOBILE_MILESTONE.md) for the base commit, independent checks, collaboration protocol and the next paid-release gates. No store approval or device test is implied by passing compilation or DOM interaction checks.
