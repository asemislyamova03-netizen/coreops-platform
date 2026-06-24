# Media Library Content Assets Plan

## Purpose

Flexity Content Factory needs a Media Library so reusable approved assets can be referenced by stable IDs instead of temporary uploaded paths.

ChatGPT-uploaded files may appear under temporary `/mnt/data` paths, but those paths are not visible to Codex or the local repository and must not be used in content packs. Content packs need stable, repo-local or storage-backed references for reusable personal-brand photos, work/process photos, generated images, Reels/TikTok assets, B-roll, brand assets, and future voice samples.

This plan is documentation-only. It does not implement the library, add folders, add media files, change publishers, or change content-pack workflows.

## Classification

- Project: Flexity
- Category: documentation_only
- Risk: medium
- Scope: content asset architecture planning for `landing/content/media-library/**`
- Not in scope: implementation, media files, publisher scripts, workflows, backend, platform-console, deploy, nginx, secrets, and content-pack edits

## Proposed Folder Structure

```text
landing/content/media-library/
  asem/
    media.yml
    photos/
      personal-brand/
      work-process/
    generated/
      carousel-drafts/
      reel-drafts/
    brand/
      logos/
      backgrounds/
      typography/
    broll/
      video/
      photos/
    voice/
      samples/
      consent/
  shared/
    media.yml
    brand/
      flexity/
```

Future private raw storage can be introduced outside public generated assets:

```text
.storage/media-private/asem/originals/
```

Rules:

- `landing/content/media-library/**` is source/control-plane storage for approved reusable publishable assets.
- `landing/www/assets/social/<slug>/` remains generated public output.
- Raw sensitive originals should not be committed.
- Temporary `/mnt/data` paths must never be referenced by content packs or manifests.

## `media.yml` Schema

Each library owner has a `media.yml` file. The schema should be readable by humans and strict enough for content tooling to validate asset eligibility before generation.

```yaml
owner: asem
library_version: 1

persona:
  name: "Асем Ислямова"
  role: "Founder"
  tone:
    - practical
    - personal
    - systems_thinking
  avoid:
    - hype
    - guru_style
    - fake_success

content_patterns:
  - personal_story
  - founder_journey
  - business_process
  - ai_assistant
  - client_case
  - behind_the_scenes
  - contentops
  - product_progress

assets:
  - id: asem_personal_001
    path: photos/personal-brand/asem-personal-001.jpg
    type: personal_brand_photo
    mood:
      - confident
      - warm
      - professional
    allowed_for:
      - telegram
      - instagram_feed
      - instagram_carousel
      - insights
    usage_rights:
      source: user_provided
      consent: approved
      commercial_use: true
      expires_at: null
      restrictions:
        - do_not_use_for_political_content
        - do_not_edit_face_shape
    notes: "Approved founder photo for personal-brand content."
    status: approved

  - id: asem_voice_001
    path: voice/samples/asem-voice-001.wav
    type: voice_sample
    mood:
      - calm
      - expert
    allowed_for:
      - voice_reference
    usage_rights:
      source: user_provided
      consent: restricted
      commercial_use: false
      expires_at: null
      restrictions:
        - no_voice_cloning
        - no_synthetic_speech_generation
    notes: "Reference-only sample. Not usable for generated speech without separate approval."
    status: restricted
```

Required top-level fields:

- `owner`
- `library_version`
- `assets[]`

Required asset fields:

- `id`
- `path`
- `type`
- `mood`
- `allowed_for`
- `usage_rights`
- `notes`
- `status`

## Controlled Vocabularies

Asset `type` values:

- `personal_brand_photo`
- `work_process_photo`
- `generated_carousel_draft`
- `generated_reel_draft`
- `brand_logo`
- `brand_background`
- `brand_texture`
- `broll_photo`
- `broll_video`
- `voice_sample`

Asset `status` values:

- `draft`
- `pending_review`
- `approved`
- `restricted`
- `archived`
- `rejected`

Suggested `allowed_for` values:

- `telegram`
- `instagram_feed`
- `instagram_carousel`
- `instagram_reel`
- `tiktok_script`
- `tiktok_video`
- `insights`
- `content_pack_draft`
- `voice_reference`
- `voice_generation`

## Persona / Brand Voice

Persona metadata should live near the media inventory because the same approved assets often depend on personal-brand context.

```yaml
persona:
  name: "Асем Ислямова"
  role: "Founder"
  tone:
    - practical
    - personal
    - systems_thinking
  avoid:
    - hype
    - guru_style
    - fake_success
```

This helps AI content agents generate in Asem's voice instead of generic SaaS language. The persona block should guide captions, hooks, story framing, and script tone, but it must not override factual accuracy or approval requirements.

## Content Patterns

The media library can expose reusable content patterns:

```yaml
content_patterns:
  - personal_story
  - founder_journey
  - business_process
  - ai_assistant
  - client_case
  - behind_the_scenes
  - contentops
  - product_progress
```

Content agents can use these patterns to pick suitable media and framing:

- `personal_story`: founder-led posts with personal-brand photos.
- `founder_journey`: progress, lessons, decisions, and constraints.
- `business_process`: process diagrams, work photos, and operational examples.
- `ai_assistant`: AI workflow screenshots, generated drafts, and assistant examples.
- `client_case`: approved case framing with anonymization unless client approval exists.
- `behind_the_scenes`: work/process photos and B-roll.
- `contentops`: content factory operations, publishing workflow, and asset reuse.
- `product_progress`: Flexity feature progress without promising unfinished capabilities as ready.

## Voice Asset Policy

Voice assets must be treated more strictly than images.

Separate permissions:

- `voice_reference`: a voice sample may be used only as a human or AI reference for tone, pacing, transcription, or script review.
- `voice_generation`: a voice sample may be used to generate synthetic speech only when separate documented consent and per-use approval exist.

Default rule:

- All voice samples are `restricted` and reference-only unless explicit per-use approval exists.

Hard safety rules:

- No automatic voice cloning.
- No synthetic speech generation without separate documented consent and approval.
- No video/audio commits without explicit approval.
- Voice samples must not be used as a fallback asset.

## Content-Pack Reference Schema

Content packs should reference media by stable asset ID, not by filesystem paths.

```yaml
media_refs:
  primary:
    id: asem_personal_001
    role: cover_photo
    required: true
  supporting:
    - id: asem_work_003
      role: process_photo
    - id: flexity_brand_bg_001
      role: carousel_background
  prohibited:
    - voice_samples
```

Rules:

- The generator resolves `id` values against `media.yml`.
- A required asset that is missing, restricted, rejected, or not approved for the target channel must fail closed.
- Content packs must never reference `/mnt/data` paths.
- Content packs should not hardcode source media paths when a library ID exists.

## Generated Output And Provenance

Generators should resolve approved media IDs and output final public assets into:

```text
landing/www/assets/social/<YYYY-MM-DD-slug>/
  instagram-feed.png
  carousel-01.png
  carousel-02.png
  reel-cover.png
  media-manifest.yml
```

The generated `media-manifest.yml` must record provenance:

```yaml
slug: 2026-06-24-example
generated_at: "2026-06-24T00:00:00+05:00"
inputs:
  - id: asem_personal_001
    source_path: landing/content/media-library/asem/photos/personal-brand/asem-personal-001.jpg
    usage: cover_photo
  - id: flexity_brand_bg_001
    source_path: landing/content/media-library/shared/brand/flexity/backgrounds/flexity-bg-001.png
    usage: carousel_background
outputs:
  - path: landing/www/assets/social/2026-06-24-example/instagram-feed.png
    channel: instagram_feed
  - path: landing/www/assets/social/2026-06-24-example/carousel-01.png
    channel: instagram_carousel
```

Required manifest fields:

- `slug`
- `generated_at`
- input asset IDs
- source paths
- usage
- generated output paths
- channel

## Safety Rules

- Do not use personal photos unless `status: approved` and `usage_rights.consent: approved`.
- Do not use voice samples unless explicitly approved for that exact use.
- No fallback to any random available face/photo.
- Missing approved media must fail closed.
- No raw sensitive/private media in the repo.
- Strip EXIF from publishable derivatives.
- Content packs must never reference temporary `/mnt/data` paths.
- Do not commit video/audio without explicit approval.
- Voice has stricter rules than images.
- Do not use generated personal-brand imagery in a way that implies a real photo unless it is clearly approved for that use.
- Do not use client/private photos in public content without explicit client approval.
- Do not publish content that promises unfinished Flexity features as ready.

## Workflow

1. User uploads photo or video.
2. Temporary ChatGPT path is not used by Codex.
3. User copies approved file into local intake or a repo-approved folder.
4. Human approves usage rights.
5. Approved derivative is added to the Media Library.
6. `media.yml` is updated.
7. Content pack references media ID.
8. Generator creates public social assets.
9. Publisher uses only generated public assets.

## Implementation Phases

### Phase 1: Documentation-only plan

Create this plan and commit only the documentation file.

### Phase 2: Empty structure and example manifest

Create empty media-library structure and example `media.yml` with no real personal media.

### Phase 3: Resolver validation

Add media resolver validation to content tooling:

- resolve asset IDs;
- validate `status`;
- validate `allowed_for`;
- reject restricted or missing media;
- reject temporary `/mnt/data` paths.

### Phase 4: Provenance manifest

Add generated `media-manifest.yml` provenance for social asset outputs.

### Phase 5: First approved Asem personal-brand photos

Add the first approved Asem personal-brand photos only after explicit approval. Use publishable derivatives, not raw originals.

### Phase 6: B-roll library for Reels/TikTok

Add B-roll categories for Reels and TikTok workflows after channel requirements are documented.

### Phase 7: Voice consent workflow

Design a separate voice consent workflow before any voice automation.

## Risks

- Personal media consent ambiguity.
- Repo bloat from large image, video, or audio files.
- EXIF/private background leakage.
- Accidental use of private photos.
- Voice misuse.
- Generated content drifting from the real personal brand.
- Channel-specific format mismatch.
- Reusing an approved asset outside its approved channel or mood.
- Confusing generated drafts with final approved public assets.

## Next Safe Step

Commit this documentation-only plan.

After that, separately approve:

1. adding the empty media-library structure and example `media.yml`;
2. adding resolver validation to content tooling;
3. adding real approved photos.

## Checks

Run:

```bash
git diff --check
git status --short
```

## Approval Status

This plan is documentation-only and does not approve implementation, media additions, publisher changes, workflow changes, backend changes, deploy changes, or voice automation.
