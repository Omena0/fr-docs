# Deploy

## GitHub Pages

The deploy-pages.yml workflow automates deployment to GitHub Pages:

1. Build docs using `fr-docs build --production`
2. Upload to GitHub Pages via `actions/upload-pages-artifact@v3`
3. Deploy via `actions/deploy-pages@v4`

## Manual Deployment

### Step 1: Build

```bash
fr-docs build --production
```

This generates static HTML files in the `docs/site/` directory.

### Step 2: Upload

Upload the contents of `docs/site/` to your hosting provider:

```bash
# For GitHub Pages (via GitHub Actions)
# OR
# For other hosting
# (e.g., S3, Netlify, Vercel, etc.)
```

### Step 3: Configure

Update your hosting's domain and path configuration.

## Versioned URLs

Fr-docs supports versioned URLs using the versioning configuration:

```json
{
  "versioning": {
    "commit_message_pattern": "^\\s*([0-9]+[A-Za-z])\\s*[-:—–]\\s*(.+)"
  }
}
```

This creates URLs like:
- `https://your-repo.pages.dev/v1/` (latest)
- `https://your-repo.pages.dev/1.0.0/` (specific version)

## Multi-environment Deployments

Use different config.json files for different environments:

```bash
# Production
fr-docs build --production --config production.json

# Staging
fr-docs build --staging --config staging.json
```
