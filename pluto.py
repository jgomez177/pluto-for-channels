import secrets, requests, json, pytz, gzip
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

class Client:
    def __init__(self):
        self.session = requests.Session()
        self.sessionAt = {}
        self.response_list = {}
        self.epg_data = {}
        self.device = None
        self.load_device()

        self.x_forward = {"local": {"X-Forwarded-For":""},
                          "uk": {"X-Forwarded-For":"178.238.11.6"},
                          "ca": {"X-Forwarded-For":"192.206.151.131"}, 
                          "us_east": {"X-Forwarded-For":"108.82.206.181"},
                          "us_west": {"X-Forwarded-For":"76.81.9.69"},}

    def load_device(self):
        try:
            with open("pluto-device.json", "r") as f:
                self.device = json.load(f)
        except FileNotFoundError:
            self.device = secrets.token_hex(12)
            with open("pluto-device.json", "w") as f:
                json.dump(self.device, f)
        return(self.device)

    def resp_data(self, country_code):
        desired_timezone = pytz.timezone('UTC')
        current_date = datetime.now(desired_timezone)
        if (self.response_list.get(country_code) is not None) and (current_date - self.sessionAt.get(country_code, datetime.now())) < timedelta(hours=4):
            return self.response_list[country_code], None
        
        boot_headers = {
            'authority': 'boot.pluto.tv',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'origin': 'https://pluto.tv',
            'referer': 'https://pluto.tv/',
            }

        boot_params = {
            'appName': 'web',
            'appVersion': '7.9.0-a9cca6b89aea4dc0998b92a51989d2adb9a9025d',
            'deviceVersion': '120.0.0',
            'deviceModel': 'web',
            'deviceMake': 'chrome',
            'deviceType': 'web',
            'clientID': self.device,
            'clientModelNumber': '1.0.0',
            'drmCapabilities': 'widevine:L3',
            }

        if country_code in self.x_forward.keys():
            boot_headers.update(self.x_forward.get(country_code))

        try:
            response = self.session.get('https://boot.pluto.tv/v4/start', headers=boot_headers, params=boot_params)
        except requests.ConnectionError as e:
            return None, f"Connection Error. {str(e)}"

        if (200 <= response.status_code <= 201):
            resp = response.json()
        else:
            print(f"HTTP failure {response.status_code}: {response.text}")
            return None, f"HTTP failure {response.status_code}: {response.text}"

        # Save entire Response:
        self.response_list.update({country_code: resp}) 
        self.sessionAt.update({country_code: current_date})
        print(f"New token for {country_code} generated at {(self.sessionAt.get(country_code)).strftime('%Y-%m-%d %H:%M.%S %z')}")

        return self.response_list.get(country_code), None

    def channels(self, country_code):
        resp, error = self.resp_data(country_code)
        if error: return None, error

        token = resp.get('sessionToken', None)
        if token is None: return None, error

        url = f"https://service-channels.clusters.pluto.tv/v2/guide/channels"

        headers = {
            'authority': 'service-channels.clusters.pluto.tv',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'authorization': f'Bearer {token}',
            'origin': 'https://pluto.tv',
            'referer': 'https://pluto.tv/',
            }

        params = {
            'channelIds': '',
            'offset': '0',
            'limit': '1000',
            'sort': 'number:asc',
            }

        if country_code in self.x_forward.keys():
            headers.update(self.x_forward.get(country_code))

        response = self.session.get(url, params=params, headers=headers)
        if response.status_code != 200:
            return None, f"HTTP failure {response.status_code}: {response.text}"
        
        channel_list = response.json().get("data")

        category_url = f"https://service-channels.clusters.pluto.tv/v2/guide/categories"

        response = self.session.get(category_url, params=params, headers=headers)
        if response.status_code != 200:
            return None, f"HTTP failure {response.status_code}: {response.text}"
        
        categories_data = response.json().get("data")

        categories_list = {}
        for elem in categories_data:
            category = elem.get('name')
            channelIDs = elem.get('channelIDs')
            for channel in channelIDs:
                categories_list.update({channel: category})

        stations = []
        for elem in channel_list:
            entry = {'id': elem.get('id'),
                    'name': elem.get('name'),
                    'slug': elem.get('slug'),
                    'tmsid': elem.get('tmsid'),
                    'group': categories_list.get(elem.get('id'))}
            
            # Ensure number value is unique
            number = elem.get('number')
            existing_numbers = {channel["number"] for channel in stations}
            while number in existing_numbers:
                # print(f"Updating channel number for {elem.get('name')}")
                number += 1

            # Filter the list to find the element with "type" equal to "colorLogoPNG"
            color_logo_png = next((image["url"] for image in elem["images"] if image["type"] == "colorLogoPNG"), None)
            entry.update({'number': number, 'logo': color_logo_png})

            stations.append(entry)

        sorted_data = sorted(stations, key=lambda x: x["number"])
        return(sorted_data, None)

    #########################################################################################
    # EPG Guide Data
    #########################################################################################
    def update_epg(self, country_code):
        resp, error = self.resp_data(country_code)
        if error: return None, error

        token = resp.get('sessionToken', None)
        if token is None: return None, error

        desired_timezone = pytz.timezone('UTC')

        start_datetime = datetime.now(desired_timezone)
        start_time = start_datetime.strftime("%Y-%m-%dT%H:00:00.000Z")
        end_time = start_time

        url = f"https://service-channels.clusters.pluto.tv/v2/guide/timelines"

        epg_headers = {
            'authority': 'service-channels.clusters.pluto.tv',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'authorization': f'Bearer {token}',
            'origin': 'https://pluto.tv',
            'referer': 'https://pluto.tv/',
            }

        epg_params = {
            'start': start_time,
            'channelIds': '',
            'duration': '720',
            }

        if country_code in self.x_forward.keys():
            epg_headers.update(self.x_forward.get(country_code))

        station_list, error = self.channels(country_code)
        if error: return None, error

        id_values = [d['id'] for d in station_list]
        group_size = 100
        grouped_id_values = [id_values[i:i + group_size] for i in range(0, len(id_values), group_size)]
        # country_data = self.epg_data.get(country_code, [])
        country_data = []

        for i in range(3):
            print(f'Retrieving {country_code} EPG data for {start_time}')
            if end_time != start_time:
                start_time = end_time
                epg_params.update({'start': start_time})
    
            for group in grouped_id_values:
                epg_params.update({"channelIds": ','.join(map(str, group))})
                response = self.session.get(url, params=epg_params, headers=epg_headers)
                if response.status_code != 200:
                    return None, f"HTTP failure {response.status_code}: {response.text}"
                country_data.append(response.json())


            end_time = datetime.strptime(response.json()["meta"]["endDateTime"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.utc).strftime("%Y-%m-%dT%H:00:00.000Z")


        self.epg_data.update({country_code: country_data})
        return None

    def epg_json(self, country_code):
        error_code = self.update_epg(country_code)
        if error_code:
            print("error") 
            return None, error_code
        return self.epg_data, None

    def find_tuples_by_value(self, dictionary, target_value):
        result_list = []  # Initialize an empty list
        for key, values in dictionary.items():
            if target_value in values:
                result_list.extend(key)  # Add the first element of the tuple to the result list
        return result_list if result_list else [target_value]  # Return None if the value is not found in any list

    def read_epg_data(self, resp, root):
        seriesGenres = {
            ("Animated",): ["Family Animation", "Cartoons"],
            ("Educational",): ["Education & Guidance", "Instructional & Educational"],
            ("News",): ["News and Information", "General News", "News + Opinion", "General News"],
            ("History",): ["History & Social Studies"],
            ("Politics",): ["Politics"],
            ("Action",):
                [
                  "Action & Adventure",
                  "Action Classics",
                  "Martial Arts",
                  "Crime Action",
                  "Family Adventures",
                  "Action Sci-Fi & Fantasy",
                  "Action Thrillers",
                  "African-American Action",
                ],
            ("Adventure",): ["Action & Adventure", "Adventures", "Sci-Fi Adventure"],
            ("Reality",):
                [
                  "Reality",
                  "Reality Drama",
                  "Courtroom Reality",
                  "Occupational Reality",
                  "Celebrity Reality",
                ],
            ("Documentary",):
                [
                  "Documentaries",
                  "Social & Cultural Documentaries",
                  "Science and Nature Documentaries",
                  "Miscellaneous Documentaries",
                  "Crime Documentaries",
                  "Travel & Adventure Documentaries",
                  "Sports Documentaries",
                  "Military Documentaries",
                  "Political Documentaries",
                  "Foreign Documentaries",
                  "Religion & Mythology Documentaries",
                  "Historical Documentaries",
                  "Biographical Documentaries",
                  "Faith & Spirituality Documentaries",
                ],
            ("Biography",): ["Biographical Documentaries", "Inspirational Biographies"],
            ("Science Fiction",): ["Sci-Fi Thrillers", "Sci-Fi Adventure", "Action Sci-Fi & Fantasy"],
            ("Thriller",): ["Sci-Fi Thrillers", "Thrillers", "Crime Thrillers"],
            ("Biography",): ["Biographical Documentaries", "Inspirational Biographies"],
            ("Talk",): ["Talk & Variety", "Talk Show"],
            ("Variety",): ["Sketch Comedies"],
            ("Home Improvement",): ["Art & Design", "DIY & How To", "Home Improvement"],
            ("House/garden",): ["Home & Garden"],
            # ("Science",): ["Science and Nature Documentaries"],
            # ("Nature",): ["Science and Nature Documentaries", "Animals"],
            ("Cooking",): ["Cooking Instruction", "Food & Wine", "Food Stories"],
            ("Travel",): ["Travel & Adventure Documentaries", "Travel"],
            ("Western",): ["Westerns", "Classic Westerns"],
            ("LGBTQ",): ["Gay & Lesbian", "Gay & Lesbian Dramas", "Gay"],
            ("Game show",): ["Game Show"],
            ("Military",): ["Classic War Stories"],
            ("Comedy",):
                [
                  "Cult Comedies",
                  "Spoofs and Satire",
                  "Slapstick",
                  "Classic Comedies",
                  "Stand-Up",
                  "Sports Comedies",
                  "African-American Comedies",
                  "Showbiz Comedies",
                  "Sketch Comedies",
                  "Teen Comedies",
                  "Latino Comedies",
                  "Family Comedies",
                ],
            ("Crime",): ["Crime Action", "Crime Drama", "Crime Documentaries"],
            ("Sports",): ["Sports","Sports & Sports Highlights","Sports Documentaries", "Poker & Gambling"],
            ("Poker & Gambling",): ["Poker & Gambling"],
            ("Crime drama",): ["Crime Drama"],
            ("Drama",):
                [
                  "Classic Dramas",
                  "Family Drama",
                  "Indie Drama",
                  "Romantic Drama",
                  "Crime Drama",
                ],
            ("Children",): ["Kids", "Children & Family", "Kids' TV", "Cartoons", "Animals", "Family Animation", "Ages 2-4", "Ages 11-12",],
            ("Animated",): ["Family Animation", "Cartoons"]
            }

        for entry in resp["data"]:
            for timeline in entry["timelines"]:
                # Create programme element
                programme = ET.SubElement(root, "programme", attrib={"channel": entry["channelId"],
                                                                 "start": datetime.strptime(timeline["start"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.utc).strftime("%Y%m%d%H%M%S %z"),
                                                                 "stop": datetime.strptime(timeline["stop"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.utc).strftime("%Y%m%d%H%M%S %z")})
                # Add sub-elements to programme
                title = ET.SubElement(programme, "title")
                title.text = timeline["title"]
                if timeline["episode"].get("series", {}).get("type", "") == "live":
                    live = ET.SubElement(programme, "live")
                elif timeline["episode"].get("series", {}).get("type", "") == "tv":
                    episode_num_onscreen = ET.SubElement(programme, "episode-num", attrib={"system": "onscreen"})
                    episode_num_onscreen.text = f'S{timeline["episode"]["season"]:02d}E{timeline["episode"]["number"]:02d}'
                    episode_num_pluto = ET.SubElement(programme, "episode-num", attrib={"system": "pluto"})
                    episode_num_pluto.text = timeline["episode"]["_id"]
                episode_num_air_date = ET.SubElement(programme, "episode-num", attrib={"system": "original-air-date"})
                episode_num_air_date.text = datetime.strptime(timeline["episode"]["clip"]["originalReleaseDate"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + 'Z'
                desc = ET.SubElement(programme, "desc")
                desc.text = (timeline["episode"]["description"]).replace('&quot;', '"')
                icon_programme = ET.SubElement(programme, "icon", attrib={"src": timeline["episode"]["series"]["tile"]["path"]})
                date = ET.SubElement(programme, "date")
                date.text = datetime.strptime(timeline["episode"]["clip"]["originalReleaseDate"], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y%m%d")
                # if timeline["episode"].get("series", {}).get("type", "") == "tv":
                series_id_pluto = ET.SubElement(programme, "series-id", attrib={"system": "pluto"})
                series_id_pluto.text = timeline["episode"]["series"]["_id"]
                if timeline["title"].lower() != timeline["episode"]["name"].lower():
                    sub_title = ET.SubElement(programme, "sub-title")
                    sub_title.text = timeline["episode"]["name"]
                categories = []
                if timeline["episode"].get("genre", None) is not None:
                    genre = timeline["episode"]["genre"]
                    result = self.find_tuples_by_value(seriesGenres, genre)
                    categories.extend(result)
                if timeline["episode"].get("series", {}).get("type", "") == "tv":
                    categories.append("Series")
                if timeline["episode"].get("series", {}).get("type", "") == "film":
                    categories.append("Movie")
                if timeline["episode"].get("subGenre", None) is not None:
                    subGenre = timeline["episode"]["subGenre"]
                    result = self.find_tuples_by_value(seriesGenres, subGenre)
                    categories.extend(result)
                # categories = sorted(categories)
                    
                unique_list = []
                for item in categories:
                    if item not in unique_list:
                        unique_list.append(item)

                for category in unique_list:
                    category_elem = ET.SubElement(programme, "category")
                    category_elem.text = category
        return root

    def create_xml_file(self, country_code):
        error_code = self.update_epg(country_code)
        if error_code: return error_code

        xml_file_path        = f"epg-{country_code}.xml"
        compressed_file_path = f"{xml_file_path}.gz"

        root = ET.Element("tv", attrib={"generator-info-name": "jgomez177", "generated-ts": ""})

        station_list, error = self.channels(country_code)
        if error: return None, error

        # Create Channel Elements from list of Stations
        for station in station_list:
            channel = ET.SubElement(root, "channel", attrib={"id": station["id"]})
            display_name = ET.SubElement(channel, "display-name")
            display_name.text = station["name"]
            icon = ET.SubElement(channel, "icon", attrib={"src": station["logo"]})

        # Create Programme Elements
        program_data =  self.epg_data.get(country_code, [])
        for elem in program_data:
            root = self.read_epg_data(elem, root)

        # Create an ElementTree object
        tree = ET.ElementTree(root)
        ET.indent(tree, '  ')

        # Create a DOCTYPE declaration
        doctype = '<!DOCTYPE tv SYSTEM "xmltv.dtd">'

        # Concatenate the XML and DOCTYPE declarations in the desired order
        xml_declaration = '<?xml version=\'1.0\' encoding=\'utf-8\'?>'
        output_content = xml_declaration + '\n' + doctype + '\n' + ET.tostring(root, encoding='utf-8').decode('utf-8')

        # Write the concatenated content to the output file
        with open(xml_file_path, "w", encoding='utf-8') as f:
            f.write(output_content)

        with open(xml_file_path, 'r') as file:
            xml_data = file.read()

        # Compress the XML file
        with open(xml_file_path, 'rb') as file:
            with gzip.open(compressed_file_path, 'wb') as compressed_file:
                compressed_file.writelines(file)

        return None
        


