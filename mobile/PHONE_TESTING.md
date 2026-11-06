# Install SlipSavvy on a real phone

This preview profile builds a standalone test app containing its JavaScript. Once installed, it does not need a local development server. It is separate from a development-client build and does not require installing Expo Go. No installable native binary has been produced or tested yet.

## Before building

Use Node 24 LTS, npm, Git and an Expo account. Work from the phone-preview branch while it is still unmerged:

```sh
git clone --branch codex/mobile-manual-review-ee57d24 https://github.com/R-Mijo/SlipSavvy.git
cd SlipSavvy/mobile
npm ci
npx eas-cli login
npx eas-cli build:configure
```

If you already have the repository, switch/update that branch rather than cloning over your existing work. The last command connects the local app to your Expo project and may add its project ID to app.json. Confirm that you are using your own Expo account/project. The preview profile is already provided in eas.json; retain it when configuring. Do not commit credentials, signing files or account tokens. No project identity or credentials are fabricated by this repository.

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

1. Add a synthetic +100 selection and review/confirm it. At $10, verify $20 total return and $10 profit.
2. Edit it to -110. Old results should disappear; recalculate and verify about $19.09 returned.
3. Check the negative-odds keyboard, bottom buttons, large text and screen-reader labels.
4. Exercise invalid odds, cancel, remove and reload. Entries currently clear on reload.
5. Record the tested commit, device/OS and observed failures in the pull request.

This phone slice has no screenshot recognition, live feed, native 100,000-run engine or billing. Compilation and installation are separate from a successful physical-device test.

References: [Expo internal distribution](https://docs.expo.dev/build/internal-distribution/), [Android APK builds](https://docs.expo.dev/build-reference/apk/), [Apple membership](https://developer.apple.com/programs/enroll/), [Expo Go version compatibility](https://docs.expo.dev/troubleshooting/expo-go-version-mismatch/).
