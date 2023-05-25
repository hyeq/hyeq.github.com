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
    {title}"""
category_format = """
category: {category}"""
permalink_format = """
permalink: {permalink}"""
redirect_format = """---
permalink: {original_filename}
---
<!DOCTYPE html>
<html>
    <head>
        <!-- <meta http-equiv="refresh" content="; url='{permalink}'" /> -->
        <meta http-equiv="refresh" content="0; url='{permalink}'" />
    </head>
    <body>
        <p>You should be immediately redirected to {permalink}. 
        If not, please click <a href="{permalink}">here</a>.</p>
    </body>
</html>
"""

def main():
    out_dir = '_pages'
    tmp_dir = 'pages-tmp'

    # Clean the pages directory and repopulate.
    shutil.rmtree(tmp_dir, ignore_errors=True)
    shutil.copytree(src_dir, tmp_dir, dirs_exist_ok=True)
    if os.path.exists(out_dir):
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

    shutil.move('_pages/index.html', 'index.html')
    # Clean up the temp directory.
    # shutil.rmtree(tmp_dir)


def translate_matlab_html_to_github_wiki_markdown(file_name, in_dir, out_dir):
    in_path = os.path.join(in_dir, file_name)
    (file_base, file_extension) = os.path.splitext(file_name)

    category = ""
    permalink_base = ""
    permalink = ""

    with open(in_path, 'r') as fp:
        soup = bs4.BeautifulSoup(fp.read(), 'html.parser', preserve_whitespace_tags=["tt", "pre", "code"])
        # soup.encode("utf8")

        # Remove the header, which tries to change the style.
        soup.html.head.decompose()

        header = soup.find(name='h1')
        if header:
            title = header.string
            header.decompose()

        # meta = soup["github pages info"]
        meta = soup.find(id="github_pages")
        if meta:
            # Because of these lines, every documentation page must have a permalink and a category, if the meta block
            # is included. They may be empty strings.
            permalink_base = meta["permalink"]
            category = meta["category"]

            print(f"Found meta. category={category}, permalink={permalink_base}")

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
            if not translate_matlab_links_to_help_into_standard_urls(link_tag):
                scrub_remaining_matlab_links_to_help_into_standard_urls(link_tag)

        # Convert equation images into MathJax.
        # MATLAB stores the LaTeX equations used to generate equation images in the alt text,
        # so we simply replace the image tag for each equation with the alt text, so that
        # GitHub will render the equations using MathJax.
        for img_tag in soup.findAll('img'):
            alt_text = img_tag.get('alt')
            # For latex_inline_equation_pattern, we match "$<equation>$" but
            # not "$$<equation>$$". See https://stackoverflow.com/a/62020002/6651650.
            latex_inline_equation_pattern = r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)"
            latex_block_equation_pattern = r"\$\$\n*((?:.\n*)*?)\$\$"
            if alt_text:
                block_eq_result = re.search(latex_block_equation_pattern, alt_text, re.MULTILINE)
                inline_eq_result = re.search(latex_inline_equation_pattern, alt_text, re.MULTILINE)
                if block_eq_result:
                    equation = block_eq_result.group(1)
                elif inline_eq_result:
                    equation = inline_eq_result.group(1)
                else:
                    warnings.warn(f"No equation found in alt text: {alt_text}")
                    continue

                # For the sets of real and natural numbers, we use bold-face font in MATLAB because (bizarrely) MATLAB
                # doesn't support the blackboard font. Here we convert to \mathbb.
                equation = equation.replace("\\mathbf{R}", "\\mathbb{R}")
                equation = equation.replace("\\mathbf{N}", "\\mathbb{N}")

                if inline_eq_result:
                    img_tag.replace_with(f"\\({equation}\\)")
                else:  # if block_eq_result:
                    img_tag.replace_with(f"\\[{equation}\\]")

        # Convert image paths images into MathJax.
        for img_tag in soup.findAll('img'):
            img_src:str = img_tag.get('src')
            # print(img_src)
            if img_src.startswith('images/'):
                img_src = '/' + img_src
            else:
                img_src = '/images/' + img_src
            img_tag['src'] = img_src

        # Delete all comments, in particular the MATLAB source code for the documentation that was included at the end
        # of each HTML file (it was being displayed by GitHub).
        for element in soup(text=lambda text: isinstance(text, Comment)):
            element.extract()

    # permalink_last = permalink.split('/')[-1]
    out_path = os.path.join(out_dir, permalink_base+".html")
    if permalink_base and not (permalink_base == file_base):
        # permalink_file_name = permalink + '.html'
        redirect_path = os.path.join(out_dir, file_name)
        print(f'Redirecting {redirect_path} to {out_path}')

        # Write the redirect file.
        with open(redirect_path, 'w', encoding="utf-8") as redirect_file:
            if category:
                category_prefix = f'/{category}'
            else:
                category_prefix = ''
            permalink = f'{category_prefix}/{permalink_base}'
            print(f'Permalink = {permalink} from base = {permalink_base} with category={category}')

            redirect_content = redirect_format.format(original_filename=file_base, permalink=permalink)
            redirect_file.write(redirect_content)
    else:
        out_path = os.path.join(out_dir, file_name)

    if not permalink:
        permalink = permalink_base

    # Check that the output file does not exist.
    if os.path.isfile(out_path):
        raise FileExistsError(f'The output file {out_path} already exists')

    # Write the output file.
    with open(out_path, 'w', encoding="utf-8") as outfile:
        # Build header
        header = jekyll_header_format.format(title=title)
        if category:
            header += category_format.format(category=category)
            # category=None
        if permalink_base:
            # header += permalink_format.format(permalink=f'/{category}/{permalink}')
            header += permalink_format.format(permalink=permalink)

        #     # permalink=None
        header += "\n---\n"
        outfile.write(header)

        outfile.write("{% raw %}\n")
        # We use formatter=None to prevent converting "&", "<", etc. into HTML entities (e.g., "&amp;")
        outfile.write(soup.prettify(formatter=None))
        outfile.write("{% endraw %}\n")
        # print(f"Wrote output to {out_path}")


def translate_matlab_links_to_help_into_standard_urls(link_tag):
    href = link_tag.get('href')
    regex_pattern = r"matlab:hybrid\.internal\.openHelp\('(.*?)(\.html)?'\)"
    result = re.match(regex_pattern, href)
    if result:
        relative_url = result.group(1)
        link_text = link_tag.string
        # Update links to use relative links instead of MATLAB commands..
        link_code = f"<a href=\"/{relative_url}\">{link_text}</a>"
        link_tag.replace_with(link_code)
        return True
    return False


def scrub_remaining_matlab_links_to_help_into_standard_urls(link_tag):
    result = re.match(r"matlab:(.*?)", link_tag.get('href'))
    if result:
        link_tag.replaceWithChildren()


main()
