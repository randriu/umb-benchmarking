import os,sys,csv,shutil
from collections import OrderedDict

TIME_DATA = "time"
SIZE_DATA = "size"

def ensure_directory(path : str):
    if not os.path.exists(path):
        os.makedirs(path)

def load_csv(path : str, prefix = None, delim='\t'):
    with open(path, 'r') as csv_file:
        table = list(csv.reader(csv_file, delimiter=delim))
    # file should have at least header row and one row of content
    if len(table) <= 1: # empty table
        return None, None
    header = table[0]
    header_indices = OrderedDict([(header[i], i) for i in range(len(header))])
    if prefix is not None:
        header = [header[0]] + sorted([h for h in header[1:] if h.startswith(prefix)])
    content = OrderedDict()
    for row in table[1:]:
        content[row[0]] = OrderedDict()
        for h in header[1:]:
            content[row[0]][h] = row[header_indices[h]]
    return content, header

def is_number(value):
    try:
        float(value)
        return True
    except:
        return False

def float_list_to_time(values : list):
    s = sorted(values)
    median = s[len(s)//2] if len(s) %2 == 1 else (s[len(s)//2 -1] + s[len(s)//2]) /2
    diff = max([abs(v - median) for v in values])
    if float("{:.2f}".format(median)) == 0.0:
        return "{:.2f}".format(median)
    return "{:.2f} (±{:.2f})".format(median, diff)

def float_list_to_size(values : list):
    s = sorted(values)
    median = s[len(s)//2] if len(s) %2 == 1 else (s[len(s)//2 -1] + s[len(s)//2]) /2
    diff = max([abs(v - median) for v in values])
    diff_percentage = int(round((diff / median) * 100))
    if diff_percentage > 0:
        return "{:.2f} MB (±{}%)".format(median / 1024 / 1024, diff_percentage)
    return "{:.2f} MB".format(median / 1024 / 1024)

def create_model_page(dir : str):
    for f in ["model.prism", "property.props", "model.jani"]:
        assert os.path.exists(os.path.join(dir, f)), "Error: File {} not found.".format(os.path.join(dir, f))
    benchmark_name = os.path.basename(dir)
    model_name = benchmark_name.split(".")[0]

    download_links = ""
    file_contents = ""
    for f in ["model.prism", "property.props", "model.jani"]:
        assert os.path.exists(os.path.join(dir, f)), "Error: File {} not found.".format(os.path.join(dir, f))
        size_in_mb = os.path.getsize(os.path.join(dir, f)) / 1024 / 1024
        download_links += "<a href=\"{}\" download>{}</a> ({:.2f} MB)\n".format(f, f, max(0.01, size_in_mb))
        if size_in_mb <= 0.3: # don't show large files
            with open(os.path.join(dir, f), 'r') as infile:
                content = infile.read()
        else:
            content = "File too large to display (size: {:.2f} MB).".format(size_in_mb)
        file_contents += """<div class="box">
<div class="boxlabelo"><div class="boxlabelc">Contents of file: {}</div></div>
<pre style="overflow:auto; padding-bottom: 1.5ex">{}</pre>
</div>
""".format(f, content)


    with open(os.path.join(dir, "index.html"), 'w') as mdfile:
        mdfile.write(r"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>%%%benchmark_name%%%</title>
<link rel="stylesheet" type="text/css" href=../../style.css>
</head>
<body>
<h3>Benchmark %%%benchmark_name%%%</h3>
<div class="box">
<div class="boxlabelo"><div class="boxlabelc">Download</div></div>
<pre style="overflow:auto; padding-bottom: 0.5ex">
%%%download_links%%%
</pre>
</div>
<div class="box">
<div class="boxlabelo"><div class="boxlabelc">Origin</div></div>
<pre style="overflow:auto; padding-bottom: 1.5ex">
Taken from <a href="https://qcomp.org/benchmarks/#%%%model_name%%%" target="_blank">QVBS</a> (January 2026).
The given benchmark (including parameter instantiation and property) has been considered in QComp 2019 and QComp 2020.

Original Prism model and property files have been adapted for compatibility and simplicity:
- Constants: All open constants are now explicitly set within model.prism (no need to set them via command line)
- Properties: The properties only refer to labels and rewards as defined in the model.prism file. No variables or constants are used in the property.
- Formulas: some PRISM formula declarations have been renamed so that their identify does not crash with a label.
</pre>
</div>
%%%file_contents%%%
</body>
</html>
""".replace("%%%benchmark_name%%%", benchmark_name).replace("%%%model_name%%%", model_name).replace("%%%download_links%%%", download_links).replace("%%%file_contents%%%", file_contents))



def create_logpage(row: str, column: str, values, logs_dir: str, out_dir: str):
    outfile_name = "{}_{}".format(row, column)
    outfile_path = os.path.join(out_dir, outfile_name + ".html")
    infile_names = sorted([f for f in os.listdir(logs_dir) if f.startswith("{}_{}".format(column, row))])
    if len(infile_names) == 0:
        return None
    modelpage_link = "<a href=\"../../models/{}/index.html\" target=\"_blank\">{}</a>".format(row, row)
    config = column
    with open(outfile_path, 'w') as outfile:
        outfile.write(r"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Log %%%outfile_name%%%</title>
<link rel="stylesheet" type="text/css" href=../../style.css>
</head>
<body>
<h3>Log files for model %%%modelpage_link%%% and tool configuration %%%config%%%</h3>
<div class="box">
<div class="boxlabelo"><div class="boxlabelc">Parsed values</div></div>
<pre style="overflow:auto; padding-bottom: 1.5ex">%%%values%%%</pre>
</div>
""".replace("%%%outfile_name%%%", outfile_name).replace("%%%config%%%", config).replace("%%%modelpage_link%%%", modelpage_link).replace("%%%values%%%", values))
        for infile_name in infile_names:
            infile_path = os.path.join(logs_dir, infile_name)
            with open(infile_path, 'r') as infile:
                log = infile.read()
            outfile.write("""<div class="box">
<div class="boxlabelo"><div class="boxlabelc">Log file: {}</div></div>
<pre style="overflow:auto; padding-bottom: 1.5ex">{}</pre>
</div>
""".format(infile_name, log))
        outfile.write("</body>\n</html>")
    return outfile_name + ".html"

def generate_table(content : OrderedDict, header : list, logs_dir: str, out_dir: str, data_type: str):
    ensure_directory(out_dir)
    logs_out_dir = os.path.join(out_dir, "logs")
    ensure_directory(logs_out_dir)
    table_name = os.path.basename(out_dir)

    first_data_col = 1
    num_cols = len(header)
    with open (os.path.join(out_dir, "index.html"), 'w') as tablefile:
        tablefile.write(r"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>%%%table_name%%% Results</title>
  <link rel="stylesheet" type="text/css" href="../style.css">
  <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.10.13/css/jquery.dataTables.min.css">
  <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/buttons/1.2.4/css/buttons.dataTables.min.css">
  <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/fixedheader/3.1.2/css/fixedHeader.dataTables.min.css">

  <script type="text/javascript" language="javascript" charset="utf8" src="https://code.jquery.com/jquery-1.12.4.js"></script>
  <script type="text/javascript" language="javascript" charset="utf8" src="https://cdn.datatables.net/1.10.13/js/jquery.dataTables.min.js"></script>
  <script type="text/javascript" language="javascript" charset="utf8" src="https://cdn.datatables.net/fixedheader/3.1.2/js/dataTables.fixedHeader.min.js"></script>
  <script type="text/javascript" language="javascript" charset="utf8" src="https://cdn.datatables.net/buttons/1.2.4/js/dataTables.buttons.min.js"></script>
  <script type="text/javascript" language="javascript" charset="utf8" src="https://cdn.datatables.net/buttons/1.2.4/js/buttons.colVis.min.js"></script>

  <script>
    $(document).ready(function() {
      // Set correct file
      $("#content").load("data.html");
    } );

    function updateBest(table) {
      // Remove old best ones
      table.cells().every( function() {
        $(this.node()).removeClass("best");
      });
      table.rows().every( function ( rowIdx, tableLoop, rowLoop ) {
          var bestValue = -1
          var bestIndex = -1
          $.each( this.data(), function( index, value ){
            if (index >= %%%first_data_col%%% && table.column(index).visible()) {
                var text = $(value).text()
                if (["TO", "ERR", "INC", "MO", "NS", "", "-"].indexOf(text) < 0) {
                    var number = parseFloat(text);
                    if (bestValue == -1 || bestValue > number) {
                      // New best value
                      bestValue = number;
                      bestIndex = index;
                    }
                  }
              }
          });
          // Set new best
          if (bestIndex >= 0) {
            $(table.cell(rowIdx, bestIndex).node()).addClass("best");
          }
      } );
  }
  </script>
</head>
""".replace("%%%table_name%%%", table_name).replace("%%%first_data_col%%%", str(first_data_col)))
        indention = 0
        def write_lines(content):
            for l in content.split("\n"):
                tablefile.write("\t"*indention + l.strip() + "\n")
        write_lines("<body>\n<div>")
        indention +=1
        write_lines("<h1>Benchmark Results: {}</h1>".format(table_name))
        write_lines('<table id="table" class="display">')
        indention += 1
        write_lines('<thead>')
        indention += 1
        write_lines('<tr>')
        indention += 1
        for head in header:
            write_lines('<th>{}</th>'.format(head))
        indention -= 1
        write_lines('</tr>')
        indention -= 1
        write_lines('</thead>\n<tbody>')
        indention += 1

        for row in content:
            write_lines('<tr>')
            indention += 1
            modelpage_link = "<a href=\"../models/{}/index.html\" target=\"_blank\">{}</a>".format(row, row)
            write_lines('<td>{}</td>'.format(modelpage_link))
            for column in header[1:]:
                assert column in content[row], "Error: missing data for model '{}' and column '{}'.".format(row, column)
                parsed_list = [x.strip() for x in content[row][column].replace("[", "").replace("]", "").split(',')]
                parsed_floats = [float(x) for x in parsed_list if is_number(x)]
                parsed_other = set([x for x in parsed_list if not is_number(x) and x != ""])
                assert all([x in ["ERR", "NS", "TO", "MO"] for x in parsed_other]), "Unexpected non-numeric values '{}' for model '{}' and column '{}'.".format(parsed_other, row, column)
                link_attributes = ""
                if "ERR" in parsed_other:
                    link_attributes = "class='error'"
                if "NS" in parsed_other:
                    link_attributes = "class='unsupported'"
                elif "TO" in parsed_other:
                    link_attributes = "class='timeout'"
                elif "MO" in parsed_other:
                    link_attributes = "class='memout'"
                cell_content = ""
                if len(parsed_floats) > 0:
                    if data_type == TIME_DATA:
                        cell_content = float_list_to_time(parsed_floats)
                    elif data_type == SIZE_DATA:
                        cell_content = float_list_to_size(parsed_floats)
                if len(parsed_other) > 0:
                    if cell_content != "":
                        cell_content += " & "
                    cell_content += ", ".join(sorted(parsed_other))
                logfile_name = create_logpage(row, column, content[row][column], logs_dir, logs_out_dir)
                if logfile_name is not None and cell_content == "":
                    cell_content = "-"
                if cell_content != "":
                    assert logfile_name is not None, "Error: No log page created for non-empty cell (model '{}', column '{}').".format(row, column)
                    cell_content = "<a href=\"logs/{}\" target=\"_blank\" {}>{}</a>".format(logfile_name, link_attributes, cell_content)
                write_lines('<td>{}</td>'.format(cell_content))
            indention -= 1
            write_lines('</tr>')
        indention -= 1
        write_lines('</tbody>')
        indention -= 1
        indention -= 1
        write_lines('</table>\n<script>')
        indention +=1
        write_lines('var table = $("#table").DataTable( {')
        indention += 1
        write_lines('"paging": false,')
        write_lines('"autoWidth": false,')
        write_lines('"info": false,')
        write_lines('fixedHeader: {')
        indention += 1
        write_lines('"header": true,')
        indention -= 1
        write_lines('},')
        write_lines('"dom": "Bfrtip",')
        write_lines('buttons: [')
        indention += 1
        for columnIndex in range(first_data_col, num_cols):
            write_lines('{')
            indention += 1
            write_lines('extend: "columnsToggle",')
            write_lines('columns: [{}],'.format(columnIndex))
            indention -= 1
            write_lines("},")
        tool_columns = [i for i in range(first_data_col, num_cols)]
        for text, show, hide in zip(["Show all", "Hide all"], [tool_columns, []], [[], tool_columns]):
            write_lines('{')
            indention += 1
            write_lines('extend: "colvisGroup",')
            write_lines('text: "{}",'.format(text))
            write_lines('show: {},'.format(show))
            write_lines('hide: {}'.format(hide))
            indention -= 1
            write_lines("},")
        indention -= 1
        write_lines("],")
        indention -= 1
        write_lines("});")
        indention -= 1
        write_lines("")
        indention += 1
        write_lines('table.on("column-sizing.dt", function (e, settings) {')
        indention += 1
        write_lines("updateBest(table);")
        indention -= 1
        write_lines("} );")
        indention -= 1
        write_lines("")
        indention += 1
        write_lines("updateBest(table);")
        indention -= 1
        write_lines("</script>")
        indention -= 1
        write_lines("</div>\n</body>\n</html>")

def write_style_file():
    with open("style.css", 'w') as stylefile:
        stylefile.write(r"""
.best {
    background-color: lightgreen;
}
.error {
    font-weight: bold;
    background-color: lightcoral;
}
.incorrect {
    background-color: orange;
    font-weight: bold;
}
.timeout {
    background-color: lightgray;
}
.memout {
    background-color: lightgray;
}
.unsupported {
    background-color: yellow;
}
.ignored {
    background-color: blue;
}

h1 {
    font-size: 28px; font-weight: bold;
    color: #000000;
    padding: 1px; margin-top: 20px; margin-bottom: 1ex;
}

tt, .tt {
    font-family: 'Courier New', monospace; line-height: 1.3;
}

.box {
    margin: 2.5ex 0ex 1ex 0ex; border: 1px solid #D0D0D0; padding: 1.6ex 1.5ex 1ex 1.5ex; position: relative;
}

.boxlabelo {
    position: absolute; pointer-events: none; margin-bottom: 0.5ex;
}

.boxlabel {
    position: relative; top: -3.35ex; left: -0.5ex; padding: 0px 0.5ex; background-color: #FFFFFF; display: inline-block;
}
.boxlabelc {
    position: relative; top: -3.17ex; left: -0.5ex; padding: 0px 0.5ex; background-color: #FFFFFF; display: inline-block;
}
""")


if __name__ == "__main__":
    print("Creates html table from CSV file. Usage:\n\tpython {} <csv directory> <log directory> <models directory>".format(sys.argv[0]))
    if len(sys.argv) != 4:
        print("Invalid number of arguments.")
        sys.exit(1)
    csv_dir, logs_dir, models_dir  = sys.argv[1:]

    write_style_file()
    print("Creating model pages ")
    ensure_directory(os.path.join("models"))
    for model_dir in os.listdir(models_dir):
        print(".", end="")
        src_dir = os.path.join(models_dir, model_dir)
        dest_dir = os.path.join("models", model_dir)
        ensure_directory(dest_dir)
        for file in ["model.prism", "property.props", "model.jani"]:
            shutil.copyfile(os.path.join(src_dir, file), os.path.join(dest_dir, file))
        create_model_page(dest_dir)
    print("")

    out_dirs = []
    for prefix in ["modest_", "prism_", "storm_"]:
        for csv_name in ["export_size", "export_time", "import_time", "full_time"]:
            csv_file = os.path.join(csv_dir, "{}.csv".format(csv_name))
            print("Creating table for {} csv file '{}'...".format(prefix, csv_file))
            if not os.path.isfile(csv_file):
                print("Error: CSV file '{}' does not exist.".format(csv_file))
                continue
            if csv_name in ["export_time", "import_time", "full_time"]:
                data_type = TIME_DATA
            elif csv_name == "export_size":
                data_type = SIZE_DATA
            else:
                raise AssertionError("Unexpected csv name: {}".format(csv_name))
            content, header = load_csv(csv_file, prefix)
            if content is None:
                print("Warning: CSV file '{}' is empty. Skipping.".format(csv_file))
                continue
            out_dir = prefix + csv_name
            generate_table(content, header, logs_dir, out_dir, data_type)
            out_dirs.append(out_dir)
    with open("index.html", 'w') as indexfile:
        indexfile.write("""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Benchmark results</title>
<link rel="stylesheet" type="text/css" href="style.css">
</head>
<body>
<h1>Benchmark results</h1>
<ul>
""")
        for out_dir in out_dirs:
            indexfile.write("<li><a href=\"{}/index.html\">{}</a></li>\n".format(out_dir, out_dir))
        indexfile.write("</ul>\n</body>\n</html>\n")

    with open("_config.yml", 'w') as cfgfile:
        cfgfile.write("name: UMB Experiments\ntitle: null")


