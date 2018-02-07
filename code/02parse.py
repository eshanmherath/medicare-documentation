import re
import os
import math
import requests
import numpy as np
import pandas as pd
import lxml.html as LH
from tabulate import tabulate
from bs4 import BeautifulSoup
from time import sleep
from glob import glob

urls_dict = {
    'Beneficiary Summary File':
        'https://www.resdac.org/cms-data/files/mbsf/data-documentation',
    'Carrier RIF':
        'https://www.resdac.org/cms-data/files/carrier-rif/data-documentation',
    'Durable Medical Equipment RIF':
        'https://www.resdac.org/cms-data/files/dme-rif/data-documentation',
    'Home Health Agency RIF':
        'https://www.resdac.org/cms-data/files/hha-rif/data-documentation',
    'Hospice RIF':
        'https://www.resdac.org/cms-data/files/hospice-rif/data-documentation',
    'Inpatient RIF':
        'https://www.resdac.org/cms-data/files/ip-rif/data-documentation',
    'MedPAR RIF':
        'https://www.resdac.org/cms-data/files/medpar-rif/data-documentation',
    'Outpatient RIF':
        'https://www.resdac.org/cms-data/files/op-rif/data-documentation',
    'Skilled Nursing Facility RIF':
        'https://www.resdac.org/cms-data/files/snf-rif/data-documentation'
}

local_paths_dict = {
    'Master Beneficiary Summary File': 'mbsf.md',
    'Carrier RIF': 'carrier-rif.md',
    'Durable Medical Equipment RIF': 'dme-rif.md',
    'Home Health Agency RIF': 'hha-rif.md',
    'Hospice RIF': 'hospice-rif.md',
    'Inpatient RIF': 'ip-rif.md',
    'MedPAR RIF': 'medpar-rif.md',
    'Outpatient RIF': 'op-rif.md',
    'Skilled Nursing Facility RIF': 'snf-rif.md'
}

for page_title, url in urls_dict.items():
    stub = re.search(r'([\w-]+)/data-documentation', url)[1]
    path = os.path.join('..', 'data', 'resdac', 'html', 'rif', stub + '.html')
    
    with open(path, 'r') as text_file:
        html = text_file.read()
    
    soup = BeautifulSoup(html, 'html.parser')
    links = LH.fromstring(html).xpath('//tr/td/a/@href')
    dfs = pd.read_html(html)

    # Create local urls to markdown anchors from title of pages
    md_anchors = []
    for link in links:
        path = os.path.join('..', 'data', 'resdac', 'html', 'variables', link[1:] + '.html')
        
        with open(path, 'r') as text_file:
            var_html = text_file.read()
        var_soup = BeautifulSoup(var_html, 'html.parser')

        md_anchor = var_soup.find(id='page-title').get_text()
        md_anchor = re.sub(r'[.,/#!$%\^&\*;:{}=_`~()]', '', md_anchor)
        md_anchor = md_anchor.strip()
        md_anchor = md_anchor.lower()
        md_anchor = md_anchor.replace(' ', '-')
        md_anchor = re.sub(r'[-]+', '-', md_anchor)
        md_anchors.append(md_anchor)

    if page_title != 'Master Beneficiary Summary File':
        table_titles = [x.get_text() for x in soup.find_all('h3')[:-1]]
        table_titles.insert(0, page_title)
    else:
        table_titles = [x.get_text() for x in soup.find_all('h3')]

    all_tables = []
    for i in range(len(dfs)):
        df = dfs[i]

        # Remove phantom 6th column:
        df = df.iloc[:, :5]

        # Add links
        df['md_anchor'] = md_anchors[:len(df)]
        md_anchors = md_anchors[len(df):]

        # Replace NaN with blank string
        df = df.fillna('')

        # Make Variable Name column a Markdown link
        df.iloc[:, 2] = (
            '[' + df.iloc[:, 2] + '](variables.md#' + df['md_anchor'] + ')')
        df = df.drop(columns=['md_anchor'])

        # Make Short SAS Name code style
        df.iloc[:, 1] = '`' + df.iloc[:, 1] + '`'

        # Write to file
        text = tabulate(
            df,
            headers=[
                'Index', 'SAS Name', 'Variable Name', 'Limitation', 'Code Table'
            ],
            tablefmt='pipe',
            showindex=False)

        all_tables.append('\n### {}\n\n'.format(table_titles[i]))
        all_tables.append(text)
        all_tables.append('\n')

    # Read in Markdown file
    fname = re.search(r'/([\w-]+)/data-documentation', url)[1]
    with open(os.path.join('..', 'docs', 'resdac', fname + '.md'), 'r') as mdfile:
        lines = mdfile.readlines()
    
    # Find the line that says "Data Documentation"
    re_text = r'(?i)\#+\s*data\s+documentation'
    line_num = [ind for ind, x in enumerate(lines) if re.search(re_text, x)]
    if line_num:
        line_num = line_num[0]
    else:
        raise ValueError('Didn\'t match any line of file')

    lines = lines[:line_num + 1]
    lines.extend(all_tables)

    with open(os.path.join('..', 'docs', 'resdac', fname + '.md'), 'w') as mdfile:
        mdfile.writelines(lines)


## Extract data from variables html pages and put into df
glob_path = os.path.join('..', 'data', 'resdac', 'html', 'variables', '**/*.html')
files = sorted(glob(glob_path, recursive=True))

# resdac_link = 'cms-data/variables/nch-claim-type-code'
# f = os.path.join('..', 'data', 'resdac', 'html', 'variables', resdac_link + '.html')

df = pd.DataFrame()
for f in files:
    with open(f, 'r') as text_file:
        html = text_file.read()
    
    resdac_url = re.search(r'/data/resdac/html/variables/(.+)\.html$', f)[1]
    resdac_url = 'https://www.resdac.org/' + resdac_url

    soup = BeautifulSoup(html, 'html.parser')
    var_title = soup.find(id='page-title').get_text()
    short_sas_name = soup.find(class_='field-name-field-short-sas-name').find(
        class_='field-item').get_text()
    try:
        long_sas_name = soup.find(class_='field-name-field-long-sas-name').find(
            class_='field-item').get_text()
    except AttributeError:
        long_sas_name = ''

    in_files = soup.find(class_='view-content').find_all('a')
    in_files = [x.get_text() for x in in_files]
    in_files = [x for x in in_files if x in local_paths_dict.keys()]

    main_text = soup.find_all(id=['block-system-main', 'region-content'])
    main_text = main_text[0].find_all('p')
    text_list = []
    for i in range(len(main_text) - 1):
        text_list.append(main_text[i].get_text())
    main_text = '\n\n'.join(text_list)

    try:
        derivation = soup.select('.field-name-field-derivation .even')
        derivation = [x.get_text() for x in derivation]
        derivation = '\n\n'.join(derivation)
        derivation = re.sub(r'\n', '\n\t', derivation)
    except:
        derivation = ''

    try:
        limitation = soup.select('.field-name-field-limitation .even')
        limitation = [x.get_text() for x in limitation]
        limitation = '\n\n'.join(limitation)
        limitation = re.sub(r'\n', '\n\t', limitation)
    except:
        limitation = ''

    # Values
    values_text = ''
    values_box = soup.find(class_='field-collection-view-final')
    if values_box is not None:
        values_text = '\n\n<h3>Values</h3>\n\n'
        if not values_box.find('tr'):
            # I.e. No table of values
            values_text += values_box.get_text()
        else:
            table_headers = [
                x.get_text()
                for x in soup.find_all(class_='field-name-field-note')
            ]
            tables = pd.read_html(html)

            all_text_tables = []
            for i in range(len(tables)):
                try:
                    all_text_tables.append(table_headers[i])
                except:
                    pass
                text_table = tabulate(
                    tables[i],
                    headers=['Code', 'Code Value'],
                    tablefmt='pipe',
                    numalign='left',
                    showindex=False)
                all_text_tables.append(text_table)

            all_text_tables = '\n\n'.join(all_text_tables)
            values_text += all_text_tables
    
    
    row = pd.DataFrame.from_dict([{
        'var_title': var_title,
        'short_sas_name': short_sas_name,
        'long_sas_name': long_sas_name,
        'in_files': in_files,
        'main_text': main_text,
        'derivation': derivation,
        'limitation': limitation,
        'values_text': values_text,
        'resdac_url': resdac_url,
        }])
    df = df.append(row)

df = df.sort_values(by = ['var_title'])
path = os.path.join('..', 'data', 'variable_info.pkl')
df.to_pickle(path)

## Import xw files:
xws = {
    'Carrier': 'carrier',
    'Inpatient': 'ip',
    'MedPAR': 'medpar',
    'Outpatient': 'op',}

all_dfs = pd.DataFrame()
for name, xw in xws.items():
    path = os.path.join('..', 'data', 'nber', 'claim_xw', xw + 'xw.txt')
    df = pd.read_table(path)
    df = df.filter(regex=(r'\d{4}'), axis = 1)
    df['Dataset'] = name
    all_dfs = all_dfs.append(df)

xw = all_dfs
xw = xw[xw['2012'].notnull()]

path = os.path.join('..', 'data', 'variable_info.pkl')
df = pd.read_pickle(path)

## Create Variable Definitions page
all_text = []
all_text.append('# Variable Definitions\n\n')
source = '!!! note\n    '
source += 'These definitions are scraped from ResDAC. Click on '
source += 'the header of a variable description to see the ResDAC page.\n\n'
all_text.append(source)

i = 0
for i in range(len(df)):
    row = df.iloc[i]

    var_title = '\n\n## [{}]({})\n\n'.format(row['var_title'], row['resdac_url'])
    varnames = '- Short SAS Name: `{}`\n'.format(row['short_sas_name'])
    if row['long_sas_name'] != '':
        varnames += '- Long SAS Name: `{}`\n'.format(row['long_sas_name'])
    varnames += '\n'

    contained_in = 'Contained in\n\n'
    for fname in row['in_files']:
        lpath = local_paths_dict[fname]
        contained_in += '- [{}]({}#data-documentation)\n'.format(fname, lpath)
    contained_in += '\n'

    text = row['main_text']
    # Format as inline code any text within '' that has at least one digit
    text = re.sub(r"'(\w*\d\w*)'", r'`\1`', text)
    text += '\n\n'

    hidden_text = []
    if row['derivation'] != '':
        derivation = '??? derivation\n\t' + row['derivation']
        hidden_text.append(derivation)
    if row['limitation'] != '':
        limitation = '??? limitation\n\t' + row['limitation']
        hidden_text.append(limitation)
    hidden_text = '\n\n'.join(hidden_text)
    
    # Show consistent names over time in a table:
    # for debugging:
    #     row = df[df['short_sas_name'].str.lower() == 'at_npi'].iloc[0]
    xw_names = xw[xw['2012'].str.lower() == row['short_sas_name'].lower()]
    xw_names = xw_names.dropna(axis=1, how='all')
    xw_names = xw_names.fillna('')
    
    cols = list(xw_names.columns)
    if cols != []:
        cols.remove('Dataset')
        cols.reverse()
        nyears = len(cols)
        ncols_to_print = 5
        ntables = math.ceil(nyears / ncols_to_print)
        
        for col in cols:
            xw_names[col] = xw_names[col].str.replace(r'(\w+)', lambda m: '`' + m.group(1) + '`')

        print_tables = ['<h3>Variable Names</h3>']
        j = 0
        for j in range(ntables):
            # Take first five:
            thiscols = cols[:ncols_to_print]
            thiscols.insert(0, 'Dataset')
            cols = cols[ncols_to_print:]
            
            tab = tabulate(
                xw_names[thiscols],
                headers='keys',
                tablefmt='pipe',
                numalign='left',
                showindex=False)
            print_tables.append(tab)
        
        print_tables = '\n\n'.join(print_tables)
        print_tables += '\n\n'
    else:
        print_tables = ''

    all_text.append(var_title)
    all_text.append(varnames)
    all_text.append(print_tables)
    all_text.append(contained_in)
    all_text.append(text)
    all_text.append(hidden_text)
    all_text.append(row['values_text'])

with open(os.path.join('..', 'docs', 'resdac', 'variables.md'), 'w') as mdfile:
    mdfile.writelines(all_text)
