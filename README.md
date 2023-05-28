# Hybrid Equations Toolbox Website
This repository contains the GitHub Pages website for the documentation of the Hybrid Equations (HyEQ) Toolbox. 

We use the `.m` documentation files as the source code to generate the documentation, so the content matches what is displayed in the MATLAB help window.
The process for generating the website requires several steps, as described below.

# Getting started.

1. Clone this repository as a directory in the root directory of the HyEQ toolbox. We'll call the directory `pages/`, for now. 
1. In the HyEQ toolbox root, run `package_toolbox` to generate HTML files (in `docs/html`) for the documentation (in `docs`).
1. In `pages/`, run `generate_github_markdown_from_docs.py` to populate `pages/_pages` from the contents of `docs/html`. 
This script cleans up the HTML from HTML to make it suitable for a GitHub pages website.  

To host the site locally (for, e.g., testing):
4. Follow the setup instructions for Jekyll and Minimal Mistakes.
1. Run `bundle` to install the required Ruby Gems.
1. Run `bundle exec jekyll serve --livereload` to launch the site. 
1. Open `http://localhost:4000/` in your web browser to view the site.