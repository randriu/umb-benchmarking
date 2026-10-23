import os
import sys
import csv

# Creates plots.tex, a LaTeX document that can be compiled with pdflatex (twice) and reproduces the plots of the paper:
# the quantile plots of the import time, export time, and file size (one row per tool) and the scatter plots of the
# total model checking time. The plots are created from the csv files of create_csv.py (the *_quantile.csv and
# full_time_median.csv files). Lines of the plots whose data is missing, e.g., the BCG files if aut_to_bcg.py was not run,
# are left out. If only a subset of the models was run, the plots show only these models.

# Numbers of the figures in the paper (the same numbers are used by create_html.py)
FIG_EFFICIENCY = 5
FIG_TOTAL_TIME = 6

# Definitions of the colors, the quantile plots and the scatter plots (copy of plots.tex of the paper)
PLOTS_TEX = r"""
%%%%%%%%%%%%%%%%
% Commands for Plots
%%%%%%%%%%%%%%%%
\newtoggle{showplots}
\toggletrue{showplots}
% \togglefalse{showplots}

%% Colours
\definecolor{plotred}{RGB}{255,0,0}
\definecolor{plotgreen}{RGB}{0,255,0}
\colorlet{plotblack}{black}
\colorlet{plotblue}{blue}
\colorlet{plotlightblue}{plotblue!60!white}
\definecolor{plotyellow}{RGB}{230,230,0}
\colorlet{plotcyan}{cyan!70!white}
\definecolor{plotorange}{RGB}{255,127,0}
\definecolor{plotpink}{RGB}{255,0,255}
\colorlet{plotgray}{gray!70!white}
\definecolor{plotdarkgray}{RGB}{128,128,128}
\definecolor{plotdarkred}{RGB}{128,0,0}
\definecolor{plotgreenyellow}{RGB}{128,128,0}
\definecolor{plotdarkgreen}{RGB}{0,128,0}
\definecolor{plotpurple}{RGB}{128,0,128}
\definecolor{plotteal}{RGB}{0,128,128}
\definecolor{plotdarkblue}{RGB}{0,0,128}
\definecolor{plotlightred}{RGB}{205,92,92}


%% Quantile Plots
\newcommand{\numinstances}{36}
\newcommand{\quantileplotxlabel}{number of models (out of \numinstances)}
\newcommand{\quantileplotylabel}{runtime (seconds)}
\newlength{\quantileplotwidth}
\newlength{\quantileplotheight}
\setlength{\quantileplotwidth}{0.6\textwidth}
\setlength{\quantileplotheight}{0.4\textwidth}
\newcommand{\quantileplotlegendcols}{1}
\newcommand{\standardquantileplotlinestyle}{ultra thick}
\newcommand{\quantileplotlinestyle}{\standardquantileplotlinestyle}

%% Configurations for Scatter Plots

\newcommand{\quantileplot}[8]{%
% Arguments:
% #1: csv filename
% #2: comma separated list of tool.config/color items}
% #3: comma separated list of readable config names
% #4: xmin
% #5: xmax
% #6: ymin
% #7: ymax
% #8: legend pos (e.g. "north west")
    \resizebox{\linewidth}{!}{%
    \begin{tikzpicture}
    \begin{axis}[
        width=\quantileplotwidth,
        height=\quantileplotheight,
        xmin=#4,
        xmax=#5,
        ymin=#6,
        ymax=#7,
        ymajorgrids,
        ymode=log,
        axis x line=bottom,
        axis y line=left,
        unbounded coords=discard,filter discard warning=false, % properly deal with missing data points
    % ytick= {1, 6, 60, 600, 1200, 1800 },
    % yticklabels={$\le$1, 6, 60, 600, 1200, 1800},
        xlabel=\quantileplotxlabel,
        xlabel style={font=\scriptsize,yshift=4pt},%{yshift=16pt},
        ylabel=\quantileplotylabel,
        ylabel style={font=\scriptsize,yshift=-7pt},%{yshift=-0.4cm},
%        log ticks with fixed point, % enable to avoid 10^-x notation
%        ytick={1,4,16,64,256,1024},
%        yticklabels={1,4,16,64,256,1024},
        yticklabel style={font=\scriptsize},
        scaled y ticks=false,
        xticklabel style={font=\scriptsize},
        legend columns=\quantileplotlegendcols,
        legend pos={#8},
        legend style={font=\scriptsize,nodes={scale=0.75, transform shape},inner sep=1pt,row sep=0pt,draw=none},
        /pgfplots/legend image code/.code={\draw[mark repeat=2,mark phase=2,##1] plot coordinates {(0cm,0cm) (0.3cm,0cm)};}, % make the legend lines a bit smaller
        every axis plot/.append style={\quantileplotlinestyle},
        legend cell align={left}
    ]
    \iftoggle{showplots}{
        \foreach \tool\color in {#2}{%
            \edef\loopbody{
                \noexpand\addplot[\color] table [x=n,y=\tool, col sep=tab] {#1};
            }
            \loopbody
        }
        \legend{#3}}{\node[anchor=south west, align=center, red] {\huge NOT\\ COMPILED};}
    \end{axis}
    \end{tikzpicture}}%
}

\newcommand{\quantileplotsize}[8]{{%
\renewcommand{\quantileplotylabel}{size (bytes)}%
\quantileplot{#1}{#2}{#3}{#4}{#5}{#6}{#7}{#8}%
}}


%% Scatter plots
\newlength\scatterplotsize
\setlength{\scatterplotsize}{0.32\textwidth}
\newcommand{\scatterplotna}{20000} % position of the "n/a" line: no result (timeout, memout, error, not supported)
\newcommand{\scatterplotmax}{40000}
\newcommand{\scatterplot}[6]{%
% Arguments:
% #1: csv filename (needs a column model_type with values mdp, dtmc, ctmc)
% #2: tool.config identifier for x-axis
% #3: label for x-axis
% #4: tool.config identifier for y-axis
% #5: label for y-axis
% #6: "false" (no legend) or a name for a shared legend (shown with \pgfplotslegendfromname{name} after the plots)
    % read the table and move missing values (nan) to the "n/a" line
    \pgfplotstableread[col sep=tab]{#1}\scattertable%
    \pgfplotstablecreatecol[create col/assign/.code={%
        \edef\scatterval{\thisrow{#2}}%
        \ifthenelse{\equal{\scatterval}{nan}}{\let\scatterval\scatterplotna}{}%
        \pgfkeyslet{/pgfplots/table/create col/next content}\scatterval}]{scatterx}\scattertable%
    \pgfplotstablecreatecol[create col/assign/.code={%
        \edef\scatterval{\thisrow{#4}}%
        \ifthenelse{\equal{\scatterval}{nan}}{\let\scatterval\scatterplotna}{}%
        \pgfkeyslet{/pgfplots/table/create col/next content}\scatterval}]{scattery}\scattertable%
    \ifthenelse{\equal{#6}{false}}{\def\scatterlegendopts{}}{\def\scatterlegendopts{legend to name={#6},legend columns=-1}}%
    \begin{tikzpicture}
    \begin{axis}[
    width=\scatterplotsize,
    height=\scatterplotsize,
    axis equal image,
    xmin=0.05,
    ymin=0.05,
    ymax=\scatterplotmax,
    xmax=\scatterplotmax,
    xmode=log,
    ymode=log,
    axis x line=bottom,
    axis y line=left,
    xtick={1,100},
    ytick={1,100},
    extra x ticks={\scatterplotna},
    extra x tick labels={n/a},
    extra x tick style={grid=major},
    extra y ticks={\scatterplotna},
    extra y tick labels={n/a},
    extra y tick style={grid=major},
    xlabel={#3},
    xlabel style={font=\scriptsize},
    ylabel={#5},
    ylabel style={font=\scriptsize,yshift=-5pt},
    yticklabel style={font=\scriptsize},
    xticklabel style={font=\scriptsize},
    \scatterlegendopts,
    legend style={font=\small,draw=none},
    scatter/classes={
        mdp={mark=*,mark size=1.5pt,plotblue},
        dtmc={mark=triangle*,mark size=2pt,plotorange},
        ctmc={mark=diamond*,mark size=2pt,plotpurple}
    }
    ]

    \iftoggle{showplots}{%
    % diagonal and lines for a factor of 10
    \addplot[no marks, forget plot] coordinates {(0.01,0.01) (\scatterplotna,\scatterplotna)};
    \addplot[no marks, densely dotted, forget plot] coordinates {(0.01,0.1) (2000,\scatterplotna)};
    \addplot[no marks, densely dotted, forget plot] coordinates {(0.1,0.01) (\scatterplotna,2000)};
    \addplot[scatter, only marks, scatter src=explicit symbolic]
    table [col sep=tab, x=scatterx, y=scattery, meta=model_type] {\scattertable};
    \ifthenelse{\NOT\equal{#6}{false}}{\legend{MDP,DTMC,CTMC}}{}
    }{\node[anchor=south west, align=center, red] {\huge NOT\\ COMPILED};}
    \end{axis}
    \end{tikzpicture}
}
"""

PREAMBLE = r"""\documentclass[a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage[paperheight=235mm, paperwidth=155mm, textwidth=12.2cm, textheight=19.3cm, twoside=false]{geometry}
\usepackage{etoolbox}
\usepackage{ifthen}
\usepackage{xcolor}
\usepackage{xspace}
\usepackage{tikz}
\usepackage{pgfplots}
\usepackage{pgfplotstable}
\usepackage{caption}
\captionsetup{labelsep=period,labelfont=bf} % captions as in the paper
\captionsetup[figure]{name=Fig.}
\pgfplotsset{compat=1.18}
\pagestyle{empty}

% Names of the tools and languages
\newcommand{\tool}[1]{\textsc{#1}\xspace}
\newcommand{\lang}[1]{\textsc{#1}\xspace}
\newcommand*{\jani}{\lang{Jani}}
\newcommand*{\UMB}{\lang{UMB}}
\newcommand*{\mcsta}{\tool{mcsta}}
\newcommand*{\prism}{\tool{Prism}}
\newcommand*{\storm}{\tool{Storm}}
"""

def sub(name, subscript):
    return name + "$_{\\mathrm{" + subscript + "}}$"

# The lines of the quantile plots: (column of the csv file, color, label)
def umb_lines(prefix, middle, suffix):
    return [(prefix + "umb" + middle + suffix, "plotblue", "UMB"),
            (prefix + "umb-gz" + middle + suffix, "plotcyan", sub("UMB", "gz")),
            (prefix + "umb-xz" + middle + suffix, "plotpurple", sub("UMB", "xz"))]

PRISM_IMPORT = [("prism_from-umb_import_ex", "plotblue", "UMB"), ("prism_from-umb-gz_import_ex", "plotcyan", sub("UMB", "gz")),
                ("prism_from-umb-xz_import_ex", "plotpurple", sub("UMB", "xz")), ("prism_from-prism_import_ex", "plotorange", "PRISM"),
                ("prism_from-tra_import_ex", "plotgreen", "TRA")]
PRISM_EXPORT = [("prism_from-prism_to-umb_ex", "plotblue", "UMB"), ("prism_from-prism_to-umb-gz_ex", "plotcyan", sub("UMB", "gz")),
                ("prism_from-prism_to-umb-xz_ex", "plotpurple", sub("UMB", "xz")), ("prism_from-prism_to-tra_ex", "plotgreen", "TRA"),
                ("prism_from-prism_to-tra-gz_ex", "plotgreenyellow", sub("TRA", "gz")), ("prism_from-prism_to-tra-xz_ex", "plotdarkgreen", sub("TRA", "xz"))]
MODEST_IMPORT = [("modest_from-umb_import_default", "plotblue", "UMB"), ("modest_from-umb-gz_import_default", "plotcyan", sub("UMB", "gz")),
                 ("modest_from-umb-xz_import_default", "plotpurple", sub("UMB", "xz")), ("modest_from-jani_import_default", "plotred", "JANI")]
MODEST_EXPORT = [("modest_from-jani_to-umb_default", "plotblue", "UMB"), ("modest_from-jani_to-umb-gz_default", "plotcyan", sub("UMB", "gz")),
                 ("modest_from-jani_to-umb-xz_default", "plotpurple", sub("UMB", "xz")), ("modest_from-jani_to-imca_default", "plotgreen", "MRM"),
                 ("modest_from-jani_to-aut_default", "plotyellow", "AUT")]
MODEST_SIZE = [("modest_from-jani_to-umb_default", "plotblue", "UMB"), ("modest_from-jani_to-aut_default", "plotyellow", "AUT"),
               ("modest_from-jani_to-umb-gz_default", "plotcyan", sub("UMB", "gz")), ("modest_bcgio_aut-to-bcg_default", "plotorange", "BCG"),
               ("modest_from-jani_to-umb-xz_default", "plotpurple", sub("UMB", "xz")), ("modest_bcgio_aut-to-bcg-gz_default", "plotred", sub("BCG", "gz")),
               ("modest_from-jani_to-imca_default", "plotgreen", "MRM"), ("modest_bcgio_aut-to-bcg-xz_default", "black", sub("BCG", "xz"))]
STORM_IMPORT = [("storm_from-umb_import_sparse", "plotblue", "UMB"), ("storm_from-umb-gz_import_sparse", "plotcyan", sub("UMB", "gz")),
                ("storm_from-umb-xz_import_sparse", "plotpurple", sub("UMB", "xz")), ("storm_from-jani_import_sparse", "plotred", "JANI"),
                ("storm_from-prism_import_sparse", "plotorange", "PRISM"), ("storm_from-jani_import_cudd", "plotpink", sub("JANI", "dd")),
                ("storm_from-drn_import_sparse", "plotgreen", "DRN")]
STORM_EXPORT = [("storm_from-jani_to-umb_sparse", "plotblue", "UMB"), ("storm_from-jani_to-umb-gz_sparse", "plotcyan", sub("UMB", "gz")),
                ("storm_from-jani_to-umb-xz_sparse", "plotpurple", sub("UMB", "xz")), ("storm_from-jani_to-drn_sparse", "plotgreen", "DRN"),
                ("storm_from-jani_to-drn-gz_sparse", "plotgreenyellow", sub("DRN", "gz")), ("storm_from-jani_to-drn-xz_sparse", "plotdarkgreen", sub("DRN", "xz"))]

# One row of plots per tool; each plot: (csv file, lines, is a size plot, number of columns of the legend)
ROWS = [
    [("import_time_quantile", PRISM_IMPORT, False, 1), ("export_time_quantile", PRISM_EXPORT, False, 1), ("export_size_quantile", PRISM_EXPORT, True, 1)],
    [("import_time_quantile", MODEST_IMPORT, False, 1), ("export_time_quantile", MODEST_EXPORT, False, 1), ("export_size_quantile", MODEST_SIZE, True, 2)],
    [("import_time_quantile", STORM_IMPORT, False, 1), ("export_time_quantile", STORM_EXPORT, False, 1), ("export_size_quantile", STORM_EXPORT, True, 1)],
]

# The scatter plots: (x column, label of the x axis, y column, label of the y axis); all from full_time_median.csv
SCATTER = [("prism_from-umb_check_ex", r"\prism / \UMB", "prism_from-prism_check_ex", r"\prism / \lang{PRISM}"),
           ("modest_from-umb_check_default", r"\mcsta / \UMB", "modest_from-jani_check_default", r"\mcsta / \jani"),
           ("storm_from-umb_check_sparse", r"\storm / \UMB", "storm_from-jani_check_sparse", r"\storm / \jani")]

def read_table(csv_dir, name):
    """ Returns the header and the number of rows of the csv file or (None, 0) if it does not exist. """
    path = os.path.join(csv_dir, name + ".csv")
    if not os.path.isfile(path):
        print("Warning: '{}' does not exist.".format(path))
        return None, 0
    with open(path, newline="") as f:
        rows = list(csv.reader(f, delimiter="\t"))
    return rows[0], len(rows) - 1

def quantile_plot(csv_dir, csv_name, lines, is_size, legend_columns, num_models):
    header, _ = read_table(csv_dir, csv_name)
    present = [l for l in lines if header is not None and l[0] in header]
    for column, _, label in lines:
        if (column, _, label) not in present:
            print("Warning: no data for '{}' in {}.csv, the line is left out.".format(column, csv_name))
    out = "    \\begin{minipage}{0.33\\textwidth}%\n"
    if present:
        if legend_columns != 1:
            out += "    \\renewcommand{\\quantileplotlegendcols}{" + str(legend_columns) + "}\n"
        out += "    \\quantileplot" + ("size" if is_size else "") + "{" + os.path.join(csv_dir, csv_name + ".csv") + "}\n"
        out += "    {\n" + ",\n".join("        {}/{}".format(c, color) for c, color, _ in present) + "\n    }\n"
        out += "    {\n" + ",\n".join("        " + label for _, _, label in present) + "\n    }\n"
        out += "    {0}{" + str(max(num_models - 1, 1)) + "}" + ("{4096}{1e9}{south east}" if is_size else "{0.1}{7200}{north west}") + "\n"
    out += "    \\end{minipage}%\n"
    return out

def empirical_figure(csv_dir, num_models):
    out = "\\setcounter{figure}{" + str(FIG_EFFICIENCY - 1) + "}\n\\begin{figure}[t]\n" + r"""    \pgfplotsset{
      every axis legend/.append style={
        font=\scriptsize,
        inner xsep=2pt,
        inner ysep=1pt,
        row sep=0pt,
      }
    }
    \renewcommand{\quantileplotwidth}{4.5cm}
    \renewcommand{\quantileplotheight}{5cm}
"""
    out += "    \\\\\n".join("".join(quantile_plot(csv_dir, *plot, num_models) for plot in row) for row in ROWS)
    out += r"""    \caption{
    Format efficiency for \prism (top), \mcsta (middle), and \storm (bottom).
    From left to right, we report (i)~the import time, (ii)~the export time, and (iii)~the file size of explicit-state formats, also including compression.
    }
    \label{fig:empirical}
\end{figure}
"""
    return out

def scatter_figure(csv_dir):
    header, _ = read_table(csv_dir, "full_time_median")
    out = "\\setcounter{figure}{" + str(FIG_TOTAL_TIME - 1) + "}\n\\begin{figure}[t]\n    \\centering\n    \\pgfplotslegendfromname{scatterlegend}\\\\\n"
    plots = []
    for i, (x, x_label, y, y_label) in enumerate(SCATTER):
        if header is None or x not in header or y not in header or "model_type" not in header:
            print("Warning: no data for the scatter plot '{}' vs. '{}', it is left out.".format(x, y))
            continue
        legend = "scatterlegend" if i == len(SCATTER) - 1 else "false"
        plots.append("    \\scatterplot{" + os.path.join(csv_dir, "full_time_median.csv") + "}{" + x + "}{" + x_label + "}{" + y + "}{" + y_label + "}{" + legend + "}")
    out += "%\n".join(plots) + "\n"
    out += r"""    \caption{Total model checking time in seconds of \prism (left), \mcsta (middle), and \storm (right) when using \UMB vs.\ a high-level language as input.}
    \label{fig:scatter}
\end{figure}
"""
    return out

if __name__ == "__main__":
    print("Creates plots.tex in the current directory, which reproduces the plots of the paper. Usage:\n\tpython {} <csv directory>\nCompile it with pdflatex (twice).".format(sys.argv[0]))
    if len(sys.argv) != 2:
        print("Invalid number of arguments.")
        sys.exit(1)
    csv_dir = sys.argv[1]
    _, num_models = read_table(csv_dir, "import_time_quantile")
    num_models = max(num_models, 2)
    plots = PLOTS_TEX.replace("\\newcommand{\\numinstances}{36}", "\\newcommand{\\numinstances}{" + str(num_models) + "}")
    with open("plots.tex", "w") as f:
        f.write(PREAMBLE + "\n" + plots + "\n\\begin{document}\n\n")
        f.write(empirical_figure(csv_dir, num_models) + "\n\\clearpage\n\n" + scatter_figure(csv_dir))
        f.write("\n\\end{document}\n")
    print("Created plots.tex ({} models).".format(num_models))
