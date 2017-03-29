#!/usr/bin/python

'''
Script that automatically builds a table of contents (TOC) for an IPython
notebook.
Returns string to paste into notebook.
'''

import sys
import json


def main(ifilepath):

    with open(ifilepath, 'r') as infile:
        notebook = json.loads(infile.read())

    cells = notebook['cells']
    titles = []

    for cell in cells:
        if cell['cell_type'] == 'markdown':

            # /!\ may be multiple headers in the markdown cell
            cell_titles = filter(lambda line: line.startswith('#'),
                                 cell['source'])
            cell_titles = map(lambda title: title.strip('\n'), cell_titles)

            for md_title in cell_titles:
                # store header importance to show it in the toc
                level = md_title.count('#') - 1
                title = md_title.lstrip('#').strip()
                titles.append((level, title))

    levels, titles = zip(*titles)
    urls = [title_.replace(' ', '-') for title_ in titles]

    toc = ['- [%s](#%s)\n' % (title, url) for title, url in zip(titles, urls)]
    toc = ['\t%s' % tt if lvl > 1 else tt for tt, lvl in zip(toc, levels)]
    toc = [tt for tt, lvl in zip(toc, levels) if lvl <= 5]

    toc = ''.join(toc)
    return toc


if __name__ == '__main__':

    ifilepath = sys.argv[1]
    toc = main(ifilepath)
print(toc)
