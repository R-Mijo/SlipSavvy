# SlipSavvy visual identity

The approved direction is a simple lime **S** with the **SlipSavvy** wordmark on charcoal. The production S is balanced under a 180-degree rotation: equal top and bottom bars, matching outer curves, matching square terminals, and no ticket notches or interior illustrations.

## Use the right version

| Where | Asset |
| --- | --- |
| Home-screen app icon / iOS base icon | `mobile/assets/icon.png` — opaque 1024 × 1024 |
| Android adaptive foreground | `mobile/assets/adaptive-foreground.png` — transparent 1080 × 1080 |
| Android themed icon | `mobile/assets/adaptive-monochrome.png` — white alpha mask |
| Native launch screen | `mobile/assets/splash-mark.png`, on charcoal |
| App header | `mobile/assets/logo-horizontal.png` |
| Full logo, transparent | `logo-stacked.png` and `logo-stacked.svg` |
| Full logo on charcoal | `logo-on-charcoal.png` |
| Compact horizontal logo | `logo-horizontal.png` and `logo-horizontal.svg` |
| Website / README | `site/assets/` and `docs/assets/banner.svg` |
| Google Play listing icon | `store/google-play-icon.png` — 512 × 512 |
| Google Play feature graphic | `store/google-play-feature.png` — 1024 × 500 |
| Social sharing artwork | `social-preview.png` — 1200 × 630 |

Use the **S alone** at small icon sizes. Use the name with the S in headers and marketing graphics. Keep the original aspect ratio and clear space. Do not add notches, sports illustrations, badges, gradients, or baked-in rounded outer corners.

The primary colors are **lime `#C9F84A`** and **charcoal `#0B1016`**. App surfaces use `#151E29`, primary text `#F1F5F9`, and secondary text `#AFBDC9`. The wordmark derives from bold Arial and is outlined in the full-logo SVGs for consistent rendering without a font dependency. PNG exports preserve the same appearance. No font files are redistributed.

## Editable source and exports

`mark.svg` is the geometric S master. The stacked and horizontal SVGs share its path. Exported PNGs are committed so installing/running the app does not require an artwork tool. To regenerate from the repository root, with Arial installed:

```sh
npm install --prefix .brand-tools @resvg/resvg-js@2.6.2 pngjs@7.0.0
node brand/export.cjs
```

The exporter is local and makes no API calls. `.brand-tools/` is ignored. Editing `mark.svg` and rerunning the exporter propagates its path into both full-logo SVGs and the platform exports.

## Rollout status

The files configure the app icon, adaptive icon, launch screen, web favicon and app header. The repository website and local Python interface also use the new identity. GitHub's README banner updates when this branch is merged. Publishing the website is a separate deployment; changing its source does not prove a live site has updated.

The Expo project remains the existing `meeho-labs/slipsavvy` project. Its verified project ID is retained in `mobile/app.json`. Native icons and launch-screen changes require a **new EAS build and installation**; the previously installed APK will retain its previous assets. Check the launch screen and icon masks on a real release/preview build. No new cloud build, store listing, or website publication is performed by exporting these files.

Store artwork is prepared for a future listing. Screenshots, listing text, policy/privacy disclosures and store review are separate release work. No Play Console or App Store Connect account is configured by this change.

References: [Expo splash-screen setup](https://docs.expo.dev/versions/latest/sdk/splash-screen/), [Android adaptive icons](https://developer.android.com/develop/ui/compose/system/icon_design_adaptive), [Google Play icon specifications](https://developer.android.com/distribute/google-play/resources/icon-design-specifications), [Google Play preview assets](https://support.google.com/googleplay/android-developer/answer/9866151).
