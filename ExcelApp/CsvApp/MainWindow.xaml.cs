using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Navigation;
using System.Windows.Shapes;
using System.IO;
using LumenWorks.Framework.IO.Csv;
using System.Dynamic;
using CsvHelper;
using System.Reflection;
using System.Diagnostics;

namespace CsvApp
{
    public class CSVItem
    {
        public string field { get; set; }
        public string product_type { get; set; }
        public string product_line { get; set; }
        public string serie { get; set; }
        public string model { get; set; }
        public string model_id { get; set; }
        public string product_id { get; set; }
        public string product_name { get; set; }
        public string folder_id { get; set; }
        public string folder_name { get; set; }
        public string sku { get; set; }
        public string part_name { get; set; }
        public string description { get; set; } 
        public string quantity { get; set; }
        public string image { get; set; }
        public bool is_scraped { get; set; }

        public static implicit operator CSVItem(ExpandoObject v)
        {
            throw new NotImplementedException();
        }
    }

    /// <summary>
    /// Interaction logic for MainWindow.xaml
    /// </summary>
    public partial class MainWindow : Window
    {
        int NUMBER_OF_HEADERS = 0;
        string basePath;
        public MainWindow()
        {
            InitializeComponent();

            String currentDirectory = Directory.GetCurrentDirectory();
            DirectoryInfo currentDirectoryInfo = new DirectoryInfo(currentDirectory);
            basePath = currentDirectoryInfo.Parent.Parent.Parent.Parent.FullName;
        }

        T GetObject<T>(IDictionary<string, object> dict)
        {
            Type type = typeof(T);
            var obj = Activator.CreateInstance(type);

            foreach (var kv in dict)
            {
                type.GetProperty(kv.Key).SetValue(obj, kv.Value);
            }
            return (T)obj;
        }

        List<CSVItem> ReadCsv(String csvPath, string[] exceptionKeys=null)
        {
            List<CSVItem> items = new List<CSVItem>();
            // open the model file in output folder which is a CSV file with headers
            using (LumenWorks.Framework.IO.Csv.CsvReader csv =
                   new LumenWorks.Framework.IO.Csv.CsvReader(new StreamReader(csvPath), true))
            {
                int fieldCount = csv.FieldCount;
                string[] headers = csv.GetFieldHeaders();
                Console.WriteLine(headers);

                this.NUMBER_OF_HEADERS = fieldCount;

                while (csv.ReadNextRecord())
                {
                    dynamic item = new ExpandoObject();
                    var dictionary = (IDictionary<string, object>)item;

                    for (int i = 0; i < fieldCount - 1; i++)
                    {
                        dictionary.Add(headers[i], csv[i]);
                    }

                    CSVItem csvItem = GetObject<CSVItem>(dictionary);

                    if (csv[fieldCount - 1] != "0")
                    {
                        csvItem.is_scraped = false;
                    }

                    items.Add(csvItem);
                }
            }

            return items;
        }

        void WriteCSV(List<CSVItem> records, string path)
        {
            if (path is null)
            {
                throw new ArgumentNullException(nameof(path));
            }

            using (var writer = new StreamWriter(path))
            using (var csv = new CsvWriter(writer))
            {
                PropertyInfo[] properties = typeof(CSVItem).GetProperties();
                foreach (PropertyInfo property in properties)
                {
                    csv.WriteField(property.Name);
                }

                csv.NextRecord();

                foreach (var record in records)
                {
                    foreach (PropertyInfo property in properties)
                    {
                        var val = property.GetValue(record);
                        if (property.Name != "is_scraped")
                        {
                            csv.WriteField(val);
                        } else
                        {
                            if ((bool)val == true)
                            {
                                csv.WriteField(1);
                            }
                            else
                            {
                                csv.WriteField(0);
                            }
                        }
                    }
                    csv.NextRecord();
                }
                writer.Flush();
            }
        }

        void LoadCSVToModelGrid(string filePath)
        {
            List<CSVItem> items = ReadCsv(filePath);

            if (this.NUMBER_OF_HEADERS > 0)
            {
                modelGrid.ItemsSource = items;
                modelGrid.Columns[this.NUMBER_OF_HEADERS - 1].DisplayIndex = 0;
            }
        }

        void LoadCSVToResultGrid(string filePath)
        {
            List<CSVItem> items = ReadCsv(filePath);

            if (this.NUMBER_OF_HEADERS > 0)
            {
                resultGrid.ItemsSource = items;
                resultGrid.Columns[this.NUMBER_OF_HEADERS - 1].DisplayIndex = 0;
            }
        }

        private void BtnLoadExistingModel(object sender, RoutedEventArgs e)
        {
            /*List<CSVItem> items = ReadCsv($"{this.basePath}\\output\\models.csv");

            if (this.NUMBER_OF_HEADERS > 0)
            {
                modelGrid.ItemsSource = items;
                modelGrid.Columns[this.NUMBER_OF_HEADERS - 1].DisplayIndex = 0;
            }*/

            LoadCSVToModelGrid($"{this.basePath}\\output\\models.csv");

        }

        private void BtnStartCrawling(object sender, RoutedEventArgs e)
        {
            var models = modelGrid.ItemsSource;
            List<CSVItem> results = new List<CSVItem>();

            if (models != null)
            {
                foreach(CSVItem item in models)
                {
                    if (item.is_scraped == true)
                    {
                        results.Add(item);
                    }
                }

                WriteCSV(results, $"{this.basePath}\\output\\filter_models.csv");

                //run_cmd("python", "--version");
                run_cmd("python", $"{this.basePath}\\crawler.py", "output");
            } else
            {
                run_cmd("python", "--version");
                MessageBox.Show("Load Models Sfirst!");
            }
        }

        private void run_cmd(string cmd, string path=null, string args=null)
        {
            ProcessStartInfo start = new ProcessStartInfo();
            start.FileName = cmd;
            start.Arguments = string.Format("{0} {1}", path, args);
            start.UseShellExecute = false;
            start.RedirectStandardOutput = true;

            using (Process process = Process.Start(start))
            {
                using (StreamReader reader = process.StandardOutput)
                {
                    string result = reader.ReadToEnd();
                    string firstLineOfResult = result.Trim().Split('\n')[0];

                    switch (firstLineOfResult.Trim())
                    {
                        case "Model Done!":
                            LoadCSVToModelGrid($"{this.basePath}\\output\\models.csv");
                            MessageBox.Show("Update Finished!");
                            break;

                        case "Done!":
                            LoadCSVToResultGrid($"{this.basePath}\\output\\output.csv");
                            MessageBox.Show("Crawling Finished!");
                            break;

                        case "Model Error!":
                            MessageBox.Show("There is an error when updating model!");
                            break;

                        case "Error!":
                            MessageBox.Show("Crawling Error!");
                            break;

                        default:
                            MessageBox.Show(result.Trim());
                            break;

                    }
                }
            }
        }

        private void BtnUpdateModel(object sender, RoutedEventArgs e)
        {
            run_cmd("python", $"{this.basePath}\\crawler.py", "model");
        }
    }
}
