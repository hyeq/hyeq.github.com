import os
import pathlib
import re
import html
import warnings

import bs4
import shutil

from bs4 import Comment

src_dir = '../doc/html'
jekyll_header_format = """---
layout: single
title: |
    {title}
---
"""

def main():
    out_dir = '_pages'
    tmp_dir = 'pages-tmp'

    # Clean the pages directory and repopulate.
    shutil.rmtree(tmp_dir, ignore_errors=True)
    shutil.copytree(src_dir, tmp_dir, dirs_exist_ok=True)
    shutil.rmtree(out_dir)
    os.mkdir(out_dir)
    shutil.move(os.path.join(tmp_dir, 'images'), os.path.join(out_dir, 'images'))

    # For each HTML file in this directory, translate it to a MarkDown file
    # that is compatible with GitHub Wiki's format.
    for file_name in os.listdir(tmp_dir):
        file_base, file_extension = os.path.splitext(file_name)
        if file_extension == '.html':
            translate_matlab_html_to_github_wiki_markdown(file_name, tmp_dir, out_dir)
        elif file_extension == '.png':
            # Put images into an 'images/' directory.
            shutil.move(os.path.join(tmp_dir, file_name), os.path.join(out_dir, 'images', file_name))
        else:
            warnings.warn(f"Skipping {file_name}")
    translate_matlab_html_to_github_wiki_markdown('TOC.html', tmp_dir, '.')
    shutil.move('TOC.html', 'index.html')

    # shutil.rmtree(tmp_dir)


def translate_matlab_html_to_github_wiki_markdown(file_name, in_dir, out_dir):
    in_path = os.path.join(in_dir, file_name)
    out_path = os.path.join(out_dir, file_name)

    with open(in_path, 'r') as fp:
        soup = bs4.BeautifulSoup(fp.read(), 'html.parser', preserve_whitespace_tags=["tt", "pre", "code"])
        # soup.encode("utf8")

        # Remove the header, which tries to change the style.
        soup.html.head.decompose()

        header = soup.find(name='h1')
        if header:
            title = header.string
            header.decompose()

        # Remove the footer "Published with MATLAB R2022b" that is appended by MATLAB.
        def is_footer(html_tag):
            return html_tag.has_attr('class') and html_tag['class'][0] == 'footer'
        tag = soup.find(is_footer)
        if tag:
            tag.decompose()

        # Remove unwanted "span" tags from comment blocks.
        unwanted_span_class_names = ["string", "keyword", "comment"]
        for span_tag in soup.findAll('span'):
            if span_tag.has_attr('class') and span_tag['class'][0] in unwanted_span_class_names:
                span_tag.replace_with(span_tag.string)

        # Translate each link from using calls to "matlab.internal.openHelp()"
        # to relative MediaWiki links.
        for link_tag in soup.findAll('a'):
            href = link_tag.get('href')
            regex_pattern = r"matlab:hybrid\.internal\.openHelp\('(.*?)(\.html)?'\)"
            result = re.match(regex_pattern, href)
            if result:
                relative_url = result.group(1)
                link_text = link_tag.string
                # Update links to use relative links instead of MATLAB commands..
                link_code = f"<a href=\"/{relative_url}\">{link_text}</a>"
                link_tag.replace_with(link_code)

        # Convert equation images into MathJax.
        # MATLAB stores the LaTeX equations used to generate equation images in the alt text,
        # so we simply replace the image tag for each equation with the alt text, so that
        # GitHub will render the equations using MathJax.
        for img_tag in soup.findAll('img'):
            alt_text = img_tag.get('alt')
            # For latex_inline_equation_pattern, we match "$<equation>$" but
            # not "$$<equation>$$". See https://stackoverflow.com/a/62020002/6651650.
            latex_inline_equation_pattern = r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)"
            latex_block_equation_pattern = r"\$\$(.*?)\$\$"
            if alt_text:
                is_equation = re.match(latex_inline_equation_pattern, alt_text)
                if is_equation:
                    block_eq_result = re.search(latex_block_equation_pattern, alt_text)
                    inline_eq_result = re.search(latex_inline_equation_pattern, alt_text)
                    if block_eq_result:
                        equation = block_eq_result.group(1)
                    elif inline_eq_result:
                        equation = inline_eq_result.group(1)
                    else:
                        warnings.warn(f"No equation found in alt text: {alt_text}")
                        continue

                    # alt_text = alt_text.replace('$', '')
                    equation = equation.replace("\\mathbf{R}", "\\mathbb{R}")
                    equation = equation.replace("\\mathbf{N}", "\\mathbb{N}")

                    if inline_eq_result:
                        img_tag.replace_with(f"\\({equation}\\)")
                    else:  # if block_eq_result:
                        img_tag.replace_with(f"\\[{equation}\\]")

        # Convert image paths images into MathJax.
        for img_tag in soup.findAll('img'):
            src = '/images/' + img_tag.get('src')
            img_tag['src'] = src


        # Delete all comments, in particular the MATLAB source code for the documentation that was included at the end
        # of each HTML file (it was being displayed by GitHub).
        for element in soup(text=lambda text: isinstance(text, Comment)):
            element.extract()

    # Write the output file.
    with open(out_path, 'w', encoding="utf-8") as outfile:
        # We use formatter=None to prevent converting "&", "<", etc. into HTML entities (e.g., "&amp;").
        outfile.write(jekyll_header_format.format(title=title))
        outfile.write("{% raw %}\n")
        outfile.write(soup.prettify(formatter=None))
        outfile.write("{% endraw %}\n")
        # print(f"Wrote output to {out_path}")


main()
