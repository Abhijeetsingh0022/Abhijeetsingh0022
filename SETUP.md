# GitHub Profile System Setup

A minimal, recruiter-focused, automated GitHub profile for **Abhijeet Singh** (`Abhijeetsingh0022`).

This system uses a **Hybrid Architecture**:
- **High-Signal Curated Content**: Professional positioning, Data Hat AI internship, categorized technical stack, and flagship project architecture (`profile.config.json`).
- **Automated Dynamic Sync**: Live repository stars, forks, languages, update dates, GitHub streak & stats cards, profile view counter, and animated contribution snake SVG (`.github/workflows/profile.yml`).

---

## 1. Directory Structure

Ensure your profile repository (`Abhijeetsingh0022/Abhijeetsingh0022`) has this structure:

```text
.
├── .github/
│   └── workflows/
│       └── profile.yml         # Scheduled workflow (runs every 6h + on push)
├── assets/
│   ├── github-contribution-grid-snake.svg
│   └── github-contribution-grid-snake-dark.svg
├── profile.config.json         # Experience, tech stack, domains, links
├── scripts/
│   └── update_profile.py       # Python profile compiler
├── README.md                   # Pre-compiled, recruiter-ready profile README
└── SETUP.md
```

---

## 2. Enable GitHub Actions Permissions (Required)

For GitHub Actions to update `README.md` and commit the contribution snake SVG:

1. Open your repository on GitHub: `https://github.com/Abhijeetsingh0022/Abhijeetsingh0022`
2. Navigate to **Settings** → **Actions** → **General**.
3. Scroll down to **Workflow permissions**.
4. Select **Read and write permissions**.
5. Check **Allow GitHub Actions to create and approve pull requests** (optional, recommended).
6. Click **Save**.

---

## 3. Push to GitHub

From your terminal:

```bash
git add .
git commit -m "feat: setup dynamic hybrid GitHub profile"
git push origin main
```

*(If your default branch is `master`, push to `master`. The workflow is configured to support both `main` and `master`.)*

---

## 4. Run the Workflow Manually (First Time)

1. Go to the **Actions** tab in your repository.
2. Under "All workflows", click **Update GitHub Profile**.
3. Click **Run workflow** → select branch `main` → click **Run workflow**.
4. Wait ~1 minute. All steps will complete with green checkmarks (✅).

---

## 5. Customization

To update your work experience, tech stack, or featured projects:
- Edit `profile.config.json`.
- Commit and push. The workflow will automatically rebuild `README.md` with live GitHub stars and metrics.
