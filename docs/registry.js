const countryNames = [
  "Afghanistan",
  "Albania",
  "Algeria",
  "American Samoa",
  "Andorra",
  "Angola",
  "Anguilla",
  "Antarctica",
  "Antigua and Barbuda",
  "Argentina",
  "Armenia",
  "Aruba",
  "Australia",
  "Austria",
  "Azerbaijan",
  "Bahamas",
  "Bahrain",
  "Bangladesh",
  "Barbados",
  "Belarus",
  "Belgium",
  "Belize",
  "Benin",
  "Bermuda",
  "Bhutan",
  "Bolivia",
  "Bosnia and Herzegovina",
  "Botswana",
  "Bouvet Island",
  "Brazil",
  "British Indian Ocean Territory",
  "British Virgin Islands",
  "Brunei",
  "Bulgaria",
  "Burkina Faso",
  "Burundi",
  "Cambodia",
  "Cameroon",
  "Canada",
  "Cape Verde",
  "Caribbean Netherlands",
  "Cayman Islands",
  "Central African Republic",
  "Chad",
  "Chile",
  "China",
  "Christmas Island",
  "Cocos (Keeling) Islands",
  "Colombia",
  "Comoros",
  "Cook Islands",
  "Costa Rica",
  "Croatia",
  "Cuba",
  "Curaçao",
  "Cyprus",
  "Czechia",
  "DR Congo",
  "Denmark",
  "Djibouti",
  "Dominica",
  "Dominican Republic",
  "Ecuador",
  "Egypt",
  "El Salvador",
  "Equatorial Guinea",
  "Eritrea",
  "Estonia",
  "Eswatini",
  "Ethiopia",
  "Falkland Islands",
  "Faroe Islands",
  "Fiji",
  "Finland",
  "France",
  "French Guiana",
  "French Polynesia",
  "French Southern and Antarctic Lands",
  "Gabon",
  "Gambia",
  "Georgia",
  "Germany",
  "Ghana",
  "Gibraltar",
  "Greece",
  "Greenland",
  "Grenada",
  "Guadeloupe",
  "Guam",
  "Guatemala",
  "Guernsey",
  "Guinea",
  "Guinea-Bissau",
  "Guyana",
  "Haiti",
  "Heard Island and McDonald Islands",
  "Honduras",
  "Hong Kong",
  "Hungary",
  "Iceland",
  "India",
  "Indonesia",
  "Iran",
  "Iraq",
  "Ireland",
  "Isle of Man",
  "Israel",
  "Italy",
  "Ivory Coast",
  "Jamaica",
  "Japan",
  "Jersey",
  "Jordan",
  "Kazakhstan",
  "Kenya",
  "Kiribati",
  "Kosovo",
  "Kuwait",
  "Kyrgyzstan",
  "Laos",
  "Latvia",
  "Lebanon",
  "Lesotho",
  "Liberia",
  "Libya",
  "Liechtenstein",
  "Lithuania",
  "Luxembourg",
  "Macau",
  "Madagascar",
  "Malawi",
  "Malaysia",
  "Maldives",
  "Mali",
  "Malta",
  "Marshall Islands",
  "Martinique",
  "Mauritania",
  "Mauritius",
  "Mayotte",
  "Mexico",
  "Micronesia",
  "Moldova",
  "Monaco",
  "Mongolia",
  "Montenegro",
  "Montserrat",
  "Morocco",
  "Mozambique",
  "Myanmar",
  "Namibia",
  "Nauru",
  "Nepal",
  "Netherlands",
  "New Caledonia",
  "New Zealand",
  "Nicaragua",
  "Niger",
  "Nigeria",
  "Niue",
  "Norfolk Island",
  "North Korea",
  "North Macedonia",
  "Northern Mariana Islands",
  "Norway",
  "Oman",
  "Pakistan",
  "Palau",
  "Palestine",
  "Panama",
  "Papua New Guinea",
  "Paraguay",
  "Peru",
  "Philippines",
  "Pitcairn Islands",
  "Poland",
  "Portugal",
  "Puerto Rico",
  "Qatar",
  "Republic of the Congo",
  "Romania",
  "Russia",
  "Rwanda",
  "Réunion",
  "Saint Barthélemy",
  "Saint Helena, Ascension and Tristan da Cunha",
  "Saint Kitts and Nevis",
  "Saint Lucia",
  "Saint Martin",
  "Saint Pierre and Miquelon",
  "Saint Vincent and the Grenadines",
  "Samoa",
  "San Marino",
  "Saudi Arabia",
  "Senegal",
  "Serbia",
  "Seychelles",
  "Sierra Leone",
  "Singapore",
  "Sint Maarten",
  "Slovakia",
  "Slovenia",
  "Solomon Islands",
  "Somalia",
  "South Africa",
  "South Georgia",
  "South Korea",
  "South Sudan",
  "Spain",
  "Sri Lanka",
  "Sudan",
  "Suriname",
  "Svalbard and Jan Mayen",
  "Sweden",
  "Switzerland",
  "Syria",
  "São Tomé and Príncipe",
  "Taiwan",
  "Tajikistan",
  "Tanzania",
  "Thailand",
  "Timor-Leste",
  "Togo",
  "Tokelau",
  "Tonga",
  "Trinidad and Tobago",
  "Tunisia",
  "Turkey",
  "Turkmenistan",
  "Turks and Caicos Islands",
  "Tuvalu",
  "Uganda",
  "Ukraine",
  "United Arab Emirates",
  "United Kingdom",
  "United States",
  "United States Minor Outlying Islands",
  "United States Virgin Islands",
  "Uruguay",
  "Uzbekistan",
  "Vanuatu",
  "Vatican City",
  "Venezuela",
  "Vietnam",
  "Wallis and Futuna",
  "Western Sahara",
  "Yemen",
  "Zambia",
  "Zimbabwe",
  "Åland Islands"
]


window.WMR_REGISTRY = {
  version: "0.1",
  groups: [
    {
      id: "D",
      title: "Dataset",
      factors: [
        {
          id: "D-Site",
          label: "Website selection",
          help: "Provide information on the websites measured. Please add one block per input source of sites.",
          repeatable: true,
          minEntries: 1,
          itemGroups: [
             {
               id: "D-Site-Source",
               label: "Input source",
               link: "D-Site-Link",
               labels: ["Id-", "Date: "],
               items: ["D-Site-Source", "D-Site-SourceId", "D-Site-Date", "D-Site-Link"]
             }
           ],
          items: [
            {
              id: "D-Site-Source",
              label: "Input source",
              help: "The source from which websites were selected.",
              type: "select",
              options: {
                "Web search": "Please specify the search procedure or refer to the section of the paper describing it.",
                "Tranco": "Please specify the Tranco ID, date, and provide a link.",
                "Majestic": null,
                "CrUX": "Please specify the date and whether a global or country list was used.",
                "Certificate Transparency Logs": "Please specify the exact service used.",
                "Phishing URL stream": "Please specify the exact service used.",
                "Own controlled applications": "Use Source Link for an artifact link specifiying the applications.",
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
            },
            {
              id: "D-Site-SourceId",
              help: "Source-specific identifier (e.g., Tranco ID).",
              label: "Source ID",
              type: "text",
            },
            {
              id: "D-Site-Link",
              label: "Source link",
              help: "Link to the source dataset (if available)",
              type: "url",
            },
            {
              id: "D-Site-Date",
              label: "Source/list date",
              help: "Date the source was created",
              type: "date",
            },
            {
              id: "D-Site-Count",
              label: "Attempted unique website count",
              help: "How many distinct websites were attempted to visit?",
              type: "number",
            },
            {
              id: "D-Site-Sampling",
              label: "Sampling strategy",
              type: "select",
              options: {
                "Top-N ranking": "Note that popular and unpopular sites might behave differently.",
                "Random sample": "Please describe the random process.",
                "Stratified sample": "Please describe the sampling process.",
                "Full available set": null,
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
            },
            {
              id: "D-Site-Removed",
              label: "Pre-crawl removals",
              type: "multi",
              options: {
                "None": null,
                "Duplicates": "Please specify the criteria for duplicates.",
                "Unreachable": "Please specify the criteria for unreachability.",
                "Category filter": "Please provide details on the categories and how they were determined.",
                "TLD filter": "Please provide details on the countries and how they were determined.",
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
            },          
            {
              id: "D-Site-CountFinal",
              label: "Final unique website count",
              help: "How many distinct websites were successfully visited?",
              type: "number",
            },
          ]
        },
        {
          id: "D-Page",
          label: "Webpage selection",
          help: "How concrete pages or URLs are obtained from selected websites.",
          items: [
            {
              id: "D-Page-Scope",
              label: "Page scope",
              help: "Whether only landing pages are measured or internal/specific pages are also visited.",
              type: "select",
              options: {
                "Landing page only": "Please keep in mind that results could differ between landing and internal pages.",
                "Landing plus internal pages": null,
                "Specific URL list": null,
                "Search/navigation-generated pages": null,
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
            },
            {
              id: "D-Page-Conversion",
              label: "Domain to landing page conversion",
              type: "multi",
              options: {
                "https://domain/": null,
                "http://domain/": null,
                "http://www.domain/": null,
                "https://www.domain/": null,
                "Provided URL unchanged": null,
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
            },
            {
              id: "D-Page-Limit",
              label: "Internal page limit",
              help: "Maximum number of pages per site. If there is no limit or only a time or depth limit, please specify that in the notes and put -1.",
              type: "number",
              dependsOn: { itemId: "D-Page-Scope", values: ["Landing plus internal pages", "Specific URL list", "Search/navigation-generated pages", "Other"] }
            },
            {
              id: "D-Page-Depth",
              label: "Internal page depth limit",
              help: "Maximum depth of internal pages visited. If there is no limit or only a time or number of pages limit, please specify that in the notes and put -1.",
              type: "number",
              dependsOn: { itemId: "D-Page-Scope", values: ["Landing plus internal pages", "Specific URL list", "Search/navigation-generated pages", "Other"] }
            },
            {
              id: "D-Page-Navigation",
              label: "Navigation strategy",
              type: "select",
              options: {
                "Breadth-first": null,
                "Depth-first": null,
                "Random crawl": null,
                "Sitemap": null,
                "Search-driven": null,
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
              dependsOn: { itemId: "D-Page-Scope", values: ["Landing plus internal pages", "Search/navigation-generated pages"] }
            },
            {
              id: "D-Page-SameSite",
              label: "Same-site lock",
              help: "Whether the crawler is restricted to the same site or domain. Also describe whether the lock was applied before or after visting the URL (server and client-side redirections may result in cross-site navigation).",
              type: "select",
              options: {
                "SameSite": null,
                "SameDomain": null,
                "SameOrigin": null,
                "SameEntity": "Please provide details on how entities are determined.",
                "No lock": "Measurements may include pages from other sites, which may affect results.",
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."

              },
              dependsOn: { itemId: "D-Page-Scope", values: ["Landing plus internal pages", "Search/navigation-generated pages"] }
            }
          ]
        },
        {
          id: "D-Other",
          label: "Other dataset factors",
          help: "Dataset information not covered by site or page selection.",
          items: [
            {
              id: "D-Other-Description",
              label: "Description",
              type: "textarea",
            }
          ]
        }
      ]
    },
    {
      id: "B",
      title: "Crawler Basis",
      factors: [
        {
          id: "B-Type",
          label: "Type of crawler",
          help: "Whether collection uses browser execution, scripts, or both.",
          items: [
            {
              id: "B-Type-Kind",
              label: "Crawler type",
              type: "select",
              options: {
                "Browser-based": null,
                "Script-based": "Single Page Applications and similar load dynamic content that may be missed.",
                "Hybrid": null,
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
            }
          ]
        },
        {
          id: "B-Instr",
          label: "Instrumentation",
          help: "Automation, instrumentation, and crawler tools. Please add one entry for each distinct tool.",
          repeatable: true,
          minEntries: 1,
          itemGroups: [
            {
              id: "B-Instr-Tool",
              label: "Tool",
              labels: ["v"],
              items: ["B-Instr-Tool", "B-Instr-Version"]
            }
          ],
          items: [
            {
              id: "B-Instr-Tool",
              label: "Tool",
              help: "The tool or framework used for crawling and data collection.",
              type: "select",
              options: {
                "OpenWPM": null,
                "Selenium": null,
                "Playwright": null,
                "Puppeteer": null,
                "Crawlee": null,
                "Scrapy": null,
                "CDP": null,
                "Custom scripts": null,
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
            },
            {
              id: "B-Instr-Version",
              help: "Exact version of the tool.",
              label: "Version",
              type: "text",
            },
            {
              id: "B-Instr-Modification",
              label: "Runtime Modification",
              help: "How the runtime was modified to collect the data. This includes any instrumentation or modification of the browser, scripts, or tools used for crawling and data collection.",
              type: "multi",
              options: {
                "None": null,
                "Injected JavaScript": null,
                "Browser extension": null,
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
            }
          ]
        },
        {
          id: "B-Brow",
          label: "Browser",
          help: "Browsers used by the crawler. Add multiple entries when several browsers or versions are used.",
          repeatable: true,
          minEntries: 1,
          dependsOn: { itemId: "B-Type-Kind", values: ["Browser-based", "Hybrid"] },
          itemGroups: [
            {
              id: "B-Brow-Browser",
              label: "Browser",
              labels: ["v"],
              items: ["B-Brow-Browser", "B-Brow-Version"]
            }
          ],
          items: [
            {
              id: "B-Brow-Browser",
              label: "Browser",
              type: "select",
              options: {
                "Chrome": null,
                "Chromium": null,
                "Firefox": null,
                "Safari": null,
                "Edge": null,
                "WebKit": null,
                "Brave": null,
                "Tor Browser": null,
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
            },
            {
              id: "B-Brow-Version",
              label: "Version",
              help: "Exact browser version",
              type: "text",
            },
          ]
        },
        {
          id: "B-UA",
          label: "User-Agent",
          help: "User-Agent strings or policy.",
          dependsOn: { itemId: "B-Type-Kind", values: ["Browser-based", "Hybrid"] },
          items: [
            {
              id: "B-UA-Policy",
              label: "User-Agent",
              help: "User-Agent policy used by the crawler.",
              type: "select",
              options: {
                "Browser default": null,
                "Fixed custom UA": "Please provide the exact User-Agent string(s) used.",
                "Rotated UA": "Please provide details on the rotation strategy and the User-Agent string pool.",
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
            }
          ]
        },
        {
          id: "B-Head",
          label: "Headful vs headless",
          dependsOn: { itemId: "B-Type-Kind", values: ["Browser-based", "Hybrid"] },
          items: [
            {
              id: "B-Head-Mode",
              label: "Head mode",
              type: "select",
              options: {
                "Headless": "Headless mode may be recognized by websites and lead to different content or behavior compared to headful mode.",
                "Headful": null,
                "Both": null,
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
            }
          ]
        },
        {
          id: "B-Set",
          label: "Settings",
          help: "Browser and crawler settings that may affect measurements.",
          dependsOn: { itemId: "B-Type-Kind", values: ["Browser-based", "Hybrid"] },
          items: [
            {
              id: "B-Set-Window",
              help: "Window size and viewport settings. Please specify the exact dimensions or the policy used to set them.",
              label: "Window dimensions",
              type: "text",
            },
            {
              id: "B-Set-Flags",
              label: "Browser flags and settings used",
              help: "Any specific browser flags, preferences, or settings that were configured.",
              type: "text"
            },
          ]
        }
      ]
    },
    {
      id: "E",
      title: "Environment",
      factors: [
        {
          id: "E-Geo",
          label: "Geolocation",
          items: [
            {
              id: "E-Geo-Location",
              label: "Crawl location",
              type: "multi",
              options: Object.fromEntries(
                countryNames.map(country => [country, null])
              )
            }
          ]
        },
        {
          id: "E-IP",
          label: "IP type",
          items: [
            {
              id: "E-IP-Type",
              label: "IP type",
              help: "Specify the type of the IP addresses used by the crawler",
              type: "multi",
              options: {
                "Residential": null,
                "Datacenter": null,
                "University": null,
                "Cloud": null,
                "Mobile": null,
                "VPN": null,
                "Tor exit node": null,
                "Unknown": null,
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
            },
            {
              id: "E-IP-Rotation",
              label: "IP rotation",
              help: "Whether and how IP addresses are rotated during crawling.",
              type: "select",
              options: {
                "Static IP": null,
                "Per site": null,
                "Per page": null,
                "Per request": null,
                "Periodic": "Please specify the rotation details.",
                "Unknown": null,
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
            }
          ]
        },
        {
          id: "E-Platform",
          label: "Crawling platform",
          items: [
            {
              id: "E-Platform-OS",
              label: "Operating system",
              help: "Specify version and configuration details in the notes.",
              type: "select",
              options: {
                "Linux": null,
                "macOS": null,
                "Windows": null,
                "Android": null,
                "iOS": null,
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
            }
          ]
        }
      ]
    },
    {
      id: "P",
      title: "Measurement Process",
      factors: [
        {
          id: "P-State",
          label: "Stateful vs stateless",
          help: "Whether the crawler maintains state (e.g., cookies, local storage) across page visits or whether it is reset.",
          items: [
            {
              id: "P-State-Mode",
              label: "State mode",
              type: "multi",
              options: {
                "Stateless": null,
                "Stateful": null,
                "Unknown": null,
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
            },
            {
              id: "P-State-Scope",
              label: "State scope",
              help: "The scope at which state is maintained or reset (e.g., per site).",
              type: "select",
              options: {
                "Per site": null,
                "Per run": null,
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
              dependsOn: { itemId: "P-State-Mode", values: ["Stateful", "Other"] }
            }
          ]
        },
        {
          id: "P-Time",
          label: "Timeouts",
          items: [
            {
              id: "P-Time-LoadEvent",
              label: "Load condition",
              help: "The condition used to determine that a page has finished loading.",
              type: "select",
              options: {
                "load": null,
                "DOMContentLoaded": null,
                "networkidle": null,
                "commit": null,
                "fixed wait only": null,
                "custom condition": null,
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
            },
            {
              id: "P-Time-Timeout",
              label: "Navigation timeout",
              help: "Maximum time to wait for page load or the load condition to be met in seconds.",
              type: "number",
            },
            {
              id: "P-Time-Dwell",
              label: "Dwell/wait time",
              help: "Time to wait on a page before moving to the next page in seconds.",
              type: "number",
            }
          ]
        },
        {
          id: "P-Interact",
          label: "Page interaction",
          items: [
            {
              id: "P-Interact-Strategy",
              label: "Interaction strategy",
              type: "multi",
              options: {
                "None": null,
                "Scroll": null,
                "Click random elements": null,
                "Scripted user flow": null,
                "Form filling": null,
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
            }
          ]
        },
        {
          id: "P-Auth",
          label: "Authentication",
          items: [
            {
              id: "P-Auth-Use",
              label: "Authentication used",
              type: "select",
              options: {
                "None": null,
                "SSO": "Please provide details in the notes",
                "Credentials": "Please provide details in the notes",
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
            }
          ]
        },
        {
          id: "P-Cookie",
          label: "Cookie interaction",
          items: [
            {
              id: "P-Cookie-Policy",
              label: "Cookie/banner handling",
              type: "select",
              options: {
                "No interaction": null,
                "Accept all": null,
                "Reject all": null,
                "Custom choice": null,
                "Measured multiple policies": null,
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
            }
          ]
        }
        // Maybe add parallelisation or data collection here
      ]
    },
    {
      id: "A",
      title: "Analysis & Reporting",
      factors: [
        {
          id: "A-Detect",
          label: "Processing code",
          items: [
            {
              id: "A-Detect-Method",
              label: "Processing code",
              help: "Please provide details on the code and methods used to process and analyze the collected data.",
              type: "text",
            }
          ]
        },
        {
          id: "A-Clean",
          label: "Data cleaning",
          items: [
            {
              id: "A-Clean-PostExclusion",
              label: "Post-crawl exclusions",
              type: "multi",
              options: {
                "None": null,
                "Outliers": "Please specify the criteria for outliers.",
                "Duplicates": "Please specify the criteria for duplicates.",
                "Bot blocks": "Please specify the criteria for bot blocks.",
                "Related-site grouping": "Please provide details on the grouping criteria and method.",
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
            },
          ]
        },
        {
          id: "A-Manual",
          label: "Manual analysis",
          items: [
            {
              id: "A-Manual-Used",
              label: "Manual work used",
              type: "select",
              options: {
                "No": null,
                "Manual annotation": null,
                "Manual validation": null,
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
            }
          ]
        }
      ]
    },
    {
      id: "N",
      title: "Nature of the Web",
      factors: [
        {
          id: "N-Bot",
          label: "Bot detection",
          items: [
            {
              id: "N-Bot-Tested",
              label: "Bot detection considered",
              type: "select",
              options: {
                "Tested": null,
                "Observed but not tested": null,
                "Not considered": null,
                "Unknown": null,
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
            }
          ]
        },
        {
          id: "N-Time",
          label: "Time",
          items: [
            {
              id: "N-Time-Design",
              label: "Temporal design",
              type: "select",
              options: {
                "Single crawl": null,
                "Repeated crawl": null,
                "Continuous crawl": null,
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
            },
            {
              id: "N-Time-Date1",
              label: "Date the first crawl started",
              type: "date",
            },
            {
              id: "N-Time-Date2",
              label: "Date the last crawl ended",
              type: "date",
            }
          ]
        },
        {
          id: "N-Rand",
          label: "Web randomness",
          items: [
            {
              id: "N-Rand-Tested",
              label: "Variation tested",
              type: "select",
              options: {
                "Full crawl repetitions": null,
                "Small-scale experiment": null,
                "Not tested": null,
                "Other": "Provide information in the notes. If the value could be common, consider updating the WebMeasurementReport registry."
              },
            }
          ]
        }
      ]
    },
    {
      id: "G",
      title: "Good Scientific Practices",
      factors: [
        {
          id: "G-Limitations",
          label: "Limitations",
          items: [
            {
              id: "G-Limitations-Discussed",
              label: "Threats to validity discussed",
              type: "select",
              options: {
                "Yes": null,
                "No": null,
              },
            }
          ]
        },
        {
          id: "G-Ethics",
          label: "Ethics",
          items: [
            {
              id: "G-Ethics-Discussed",
              label: "Ethics discussed",
              type: "select",
              options: {
                "Yes": null,
                "No": null,
              },
            },
          ]
        },
        {
          id: "G-Open",
          label: "Open Science",
          items: [
            {
              id: "G-Open-Code",
              label: "Code availability",
              type: "select",
              options: {
                "Public": "Please provide a link in the notes.",
                "Available on request": "Please specify how to obtain the information in the notes.",
                "Partially available": "Please specify which parts are available and how to obtain them in the notes.",
                "Not available": "Please justify why the code cannot be shared in the notes.",
              },
            },
            {
              id: "G-Open-Data",
              label: "Data availability",
              type: "select",
              options: {
                "Raw and processed public": "Please provide a link in the notes.",
                "Processed public": "Please provide a link in the notes.",
                "Available on request": "Please specify how to obtain the information in the notes.",
                "Partially available": "Please specify which parts are available and how to obtain them in the notes.",
                "Not available": "Please justify why the data cannot be shared in the notes.",
              },
            },
          ]
        }
      ]
    }
  ]
};