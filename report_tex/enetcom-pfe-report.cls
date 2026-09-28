\usepackage{silence}
\WarningsOff*
\LoadClassWithOptions{report}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Packages to use
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\usepackage[a4paper,left=2.5cm,right=2.5cm,top=2.5cm,bottom=2.5cm]{geometry}
\usepackage{environ}
\usepackage{verse}
\usepackage[table]{xcolor}
\usepackage[explicit]{titlesec}
\usepackage{chngcntr}
\usepackage{fancyhdr}
\usepackage{caption}
\usepackage{subcaption}
\usepackage[hidelinks]{hyperref}
\usepackage{needspace}
\usepackage{pdfpages}
\usepackage{chngcntr}
\usepackage{enumitem}
\usepackage[bottom]{footmisc}
\usepackage[english]{babel}
\usepackage[english]{varioref}
\usepackage{acronym}
\usepackage[english]{minitoc}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Include required packages
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%\usepackage{showframe}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[skins]{tcolorbox}
\usepackage[english]{babel}
\usepackage[english]{varioref}
\usepackage[english]{adjustbox}
\usepackage{setspace}
\usepackage{minted}
\usepackage{color}
\usepackage{tabularx}
\usepackage{ctable}
\usepackage{graphicx}
\usepackage{multirow}
\usepackage{tikz}
\usepackage{seqsplit}
\usepackage{fontenc}
\usepackage{wrapfig}
\usepackage{setspace}
\usepackage[all]{nowidow}
\usepackage{acronym}
\usepackage{array,ragged2e}
\usepackage{enumitem}
\usepackage{xcolor}
\definecolor{Gris1}{RGB}{116,134,170}
\definecolor{Gris2}{RGB}{249,249,249}
\usepackage{lettrine}
\usepackage{mhchem}
\usepackage{amssymb}
\usepackage{natbib} % bibliotheque
\usepackage{multibib} % bibliotheque
\usepackage{amsmath}
\usepackage{interval}
\usepackage{csquotes}

\usepackage[titletoc,title]{appendix}

\def\defaultFont{ptm}
\renewcommand*{\familydefault}{\defaultFont}
\renewcommand\UrlFont{\ignore{Actually do nothing!}}
\sloppy



%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Define styles
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\newlength\BoxWd
\setlength\BoxWd{10mm}
\newlength\Aux

% chapter tiltes formatting
\titleformat{\chapter}[display]
{\fontsize{20}{6}\bfseries\selectfont
  \settowidth\Aux{\textcolor{white}{\Huge\thechapter}}
  \ifnum\Aux>\BoxWd
    \setlength\BoxWd{\Aux}
  \else\fi
}
{
  {\hspace*{-1.5mm}\normalfont\fontsize{14}{6}\selectfont{Chapter}}\\
  \colorbox{black}{
    \parbox[c][20mm][t]{\BoxWd}{
      \vspace{2.5mm}\centering\textcolor{white}{\Huge\thechapter}
    }
  }
}
{-10mm}
{
  \vspace{-5mm}\hspace*{15mm}\titlerule\\\\\hspace*{15mm}#1
}

  % chapter tiltes formatting
  \titleformat{name=\chapter, numberless}[display]
    {\fontsize{26}{6}\bfseries\selectfont
      \settowidth\Aux{\textcolor{white}{\Huge\thechapter}}
      \ifnum\Aux>\BoxWd
        \setlength\BoxWd{\Aux}
      \else\fi
    }
    {
      {\hspace*{-1.5mm}\normalfont\fontsize{14}{6}\selectfont{~}}\\%
      \colorbox{black}{%
        \parbox[c][20mm][t]{\BoxWd}{%
          \vspace{2.5mm}\centering\textcolor{white}{~}
        }
      }
    }
    {-10mm}
    {
      \vspace{-5mm}\hspace*{15mm}\titlerule\\\\\hspace*{15mm}#1%
    }

% chapter tiltes spacing
\titlespacing*{\chapter}{0pt}{0pt}{50pt}

\titleformat{\section}[block]%
  {\Large\bfseries}{\thesection}%
  {10pt}{\Large{\bfseries{#1}}}

\titleformat{\paragraph}[block]%
  {\normalfont\normalsize\bfseries}%
  {\theparagraph}{1em}{#1}

% \captionsetup[figure]{name={Figure}}
\captionsetup{labelfont=bf,font={singlespacing},justification=RaggedRight,font=small,textfont=sc, textfont=bf }
%\counterwithin{{figure}{chapter}
%\renewcommand{\figurename}{Figure}
%\counterwithin{table}{chapter}
%\renewcommand{\tablename}{Table}


%%%%%%%%%%%% My style begin :p%%%%%%%%%%%%

\fancypagestyle{MyStyle}{
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{1pt}
\fancyhead[L]{}
\fancyhead[R]{}
\fancyfoot[L]{\fontsize{10}{12}\selectfont\slshape \ecole \hspace{5pt}}
\fancyfoot[R]{\fontsize{12}{12}\selectfont\slshape Page \thepage}
}

\renewcommand{\chaptermark}[1]{\markboth{\MakeUppercase{#1}}{}}

%%%%%%%%%%%% My style end %%%%%%%%%%%%%
\fancypagestyle{plain}{
  \fancyhf{}
\renewcommand{\headrulewidth}{1pt}
\renewcommand{\footrulewidth}{1pt}
\fancyhead[L]{\fontsize{10}{12}\selectfont\slshape \reportTitle \hspace{5pt}}
\fancyhead[R]{\fontsize{10}{12}\selectfont\slshape \hspace{5pt} \reportAuthor}
\fancyfoot[L]{\fontsize{10}{12}\selectfont\slshape \ecole \hspace{5pt}}
\fancyfoot[R]{\fontsize{12}{12}\selectfont\slshape Page \thepage}
}

\setlength{\fboxsep}{0mm}%
\setlength{\fboxrule}{1pt}%

% Set the footnote counter to be continuous over the whole document
\counterwithout{footnote}{chapter}
\counterwithout{figure}{chapter} % Pour les figures
\counterwithout{table}{chapter} % Pour les tableaux
\counterwithout{equation}{chapter} % Pour les équations
\counterwithout{enumi}{chapter} % Pour les références bibliographiques
\counterwithout{enumi}{section} % Pour les références bibliographiques
\counterwithout{enumi}{subsection} % Pour les références bibliographiques
\pagestyle{plain}% Set page style to plain.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Useful commands
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\newcommand{\ignore}[2]{\hspace{0mm}#2}

\newcommand{\HRule}[1][\linewidth]{
  \rule{#1}{0.5mm}%
}

\newcommand{\printBigName}{%
\leavevmode\color{titleColorGray}\setmainfont{Cambria}\fontsize{23pt}{23pt}\selectfont\textbf{\@name}
}

\newcommand{\putPhoto}[1] {
  \includegraphics[width=35mm, height=35mm]{#1}
}

\newcommand{\highlight}[1] {
  \textit{#1}
}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Init commands
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\setcounter{secnumdepth}{5}
\setcounter{tocdepth}{3}

\renewcommand\theparagraph{\alph{paragraph})}
\renewcommand\thesubparagraph{\roman{subparagraph}.}

\setlength{\parskip}{1ex} % Spacing between paragraphs
% \setlist[enumerate]{itemsep=-0.35\baselineskip} % Spacing in enumerates

% \captionsetup[table]{name=Tableau}

\newcites{images}{Bibliography of Images}


% Remove hyphens
% \hyphenpenalty=10000
% \exhyphenpenalty=10000

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% New Environments
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  % all of the pfe redaction goes here
  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    \NewEnviron{pfe-enetcom} {
      \begingroup
      \BODY
      \endgroup
    }

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Allow more flexible line breaks
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\sloppy

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Supprimer l'indentation pour tous les paragraphes de texte normal
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% \setlength{\parindent}{0pt}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Configuration des énumérations
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\setlist[itemize,1]{label=\large\textendash} % Level 1: -
\setlist[itemize,2]{label=\large\textbullet} % Level 2: .