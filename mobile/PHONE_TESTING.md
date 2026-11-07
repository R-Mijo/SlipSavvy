# Install SlipSavvy on a real phone

This preview profile builds a standalone test app containing its JavaScript. Once installed, it does not need a local development server. It is separate from a development-client build and does not require installing Expo Go. An earlier Android APK was built and installed successfully; the newest selection-only parlay browser and report cards require another build. iPhone physical-device testing remains pending.

## Existing project: update the preview

The existing Expo project is already linked in `app.json` (`c89b20b7-c475-41c5-850f-a2b91da0d2b9`). Retain this identity and the current signing credentials. Do not repeat project creation for this update. Save or commit local configuration edits before updating the branch; do not discard unrelated changes. After updating, run `npm ci` and build the preview again:

```powershell
npx.cmd eas-cli build --platform android --profile preview
```

Install the new APK from the resulting EAS build page. Confirm the SlipSavvy identity, date/time-zone filters, parlay tray and report cards. Native icon/splash changes need a rebuild; refreshing the old app is insufficient. The data browser additionally needs its hosted endpoint and preview access configured as described in `server/README.md`.

Brand files and future store graphics are documented in [`brand/README.md`](../brand/README.md).

## First-time setup reference

Use Node 24 LTS, npm, Git and an Expo account. For a new checkout, start from main after the intended PR is reviewed and merged:

```sh
git clone https://github.com/R-Mijo/SlipSavvy.git
cd SlipSavvy/mobile
npm ci
npx eas-cli login
npx eas-cli build:configure
```

If you already have the repository, switch/update your intended branch rather than cloning over your existing work. The last command connects the local app to your Expo project and may add its project ID to app.json. Confirm that you are using your own Expo account/project. The preview profile is already provided in eas.json; retain it when configuring. Do not commit credentials, signing files or account tokens. No project identity or credentials are fabricated by this repository.

Expo performs the native compilation in its cloud. This route can be initiated from Windows and does not require a local Mac/Xcode installation. Build availability, queue and charges depend on your Expo account and plan; review any quoted charges before proceeding.

## Android

```sh
npx eas-cli build --platform android --profile preview
```

Let EAS manage the Android signing key if setting up a new project. When the build finishes, open its installation link or scan the QR code on the Android phone. Download the APK and follow Android's prompts to allow installation from that source. Open SlipSavvy. A Google Play account or public store listing is not required for this direct APK route. An AAB is not the directly installable format.

## iPhone

This cloud/ad-hoc route requires an active Apple Developer Program membership and access to the signing team. Apple's published membership price is USD 99 per year (local pricing/taxes can differ). This is not a requirement to pay before testing the Android preview. A free Apple account with a Mac/Xcode offers a different, more limited local testing route.

Register the physical iPhone before creating its build:

```sh
npx eas-cli device:create
npx eas-cli build --platform ios --profile preview
```

Open the device-registration URL on the actual iPhone and complete the registration steps. During the build, sign in to Apple through the EAS prompts and select the correct team; EAS can manage the signing certificate and provisioning profile. The phone must be included in that profile. After the build completes, open its installation link on that iPhone, install the app and follow any iOS trust/Developer Mode instructions that apply. If adding another phone afterward, register it and rebuild or re-sign with a profile including it.

This internal build does not submit an App Store listing. TestFlight is an alternative distribution milestone, not required for this first registered-device test.

## First test on either phone

1. Confirm the device time zone is selected automatically. Change it to New York, Phoenix and Tokyo; verify local date, time, daylight-saving behavior and morning/afternoon/night groups against the same event.
2. Browse NCAA games by available date and day part. Check eight-game pages, empty groups and market changes retaining the chosen game when available.
3. Tap multiple provider lines into the parlay. Confirm no manual selection/event/odds fields appear, removing a leg works, and the extra-leg illustration is clearly hypothetical.
4. Analyze two markets from one game plus another game. Verify each leg has a compact report and all seven responses, matching underlying event research, exact prices, source timestamps and explicit missing-data states. Default missing forecasts must not appear as numerical win estimates.
5. Test expired lines, changed prices, unavailable provider, cancelling, and changing a stake/pick during analysis. Old reports must not return. Check that changing only the time zone reformats an existing report without another provider request.
6. Check safe areas, touch targets, long names, keyboard access for optional stake/return amounts, large text and VoiceOver/TalkBack. Entries and time-zone preferences clear on reload.
7. Record commit, device/OS and failures in GitHub. Existing APKs will not gain this revision until rebuilt and installed.

This slice has no screenshot/share recognition, supported whole-parlay forecast, offered alternate-line optimizer, native 100,000-run engine or billing. Compilation, installation and a physical-device test are separate checks. Do not publish the provider key in client configuration or reports.

References: [Expo internal distribution](https://docs.expo.dev/build/internal-distribution/), [Android APK builds](https://docs.expo.dev/build-reference/apk/), [Apple membership](https://developer.apple.com/programs/enroll/), [Expo Go version compatibility](https://docs.expo.dev/troubleshooting/expo-go-version-mismatch/).
