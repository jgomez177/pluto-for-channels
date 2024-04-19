# Pluo for Channels (Python)

Current version: **1.12a**

# About
This takes Pluto Live TV Channels and generates an M3U playlist and EPG XMLTV file.

# Changes
 - Version 1.12:
    - Changed HLS Stitcher to version 1 until “Playlist had no segments” issues can be resolved in version 2
 - Version 1.11: 
    - Modified options for playlist to include a compatibility URL parameter.
    - Illegal character XML handling has been added.
 - Version 1.10: 
    - Added tvc-guide-description to playlist
 - Version 1.09: 
    - Added group-title to playlist

# Running
The recommended way of running is to pull the image from [GitHub](https://github.com/jgomez177/pluto-for-channels/pkgs/container/pluto-for-channels).

    docker run -d --restart unless-stopped --network=host -e PLUTO_PORT=[your_port_number_here] --name pluto-for-channels ghcr.io/jgomez177/pluto-for-channels
or

    docker run -d --restart unless-stopped -p [your_port_number_here]:7777 --name  pluto-for-channels ghcr.io/jgomez177/pluto-for-channels

You can retrieve the playlist and EPG via the status page.

    http://127.0.0.1:[your_port_number_here]

## Environement Variables
| Environment Variable | Description | Default |
|---|---|---|
| PLUTO_PORT | Port the API will be served on. You can set this if it conflicts with another service in your environment. | 7777 |
| PLUTO_CODE | What country streams will be hosted. <br>Multiple can be hosted using comma separation<p><p>ALLOWED_COUNTRY_CODES:<br>**us_east** - United States East Coast,<br>**us_west** - United States West Coast,<br>**local** - Local IP address Geolocation,<br>**ca** - Canada,<br>**uk** - United Kingdom,  | local,us_west,us_east,ca,uk |

## Additional URL Parameters
| Parameter | Description |
|---|---|
| channel_id_format | default channel-id is set as \"pluto-{slug}\".<br>**"id"** will change channel-id to \"pluto-{id}\".<br>**"slug_only"** will change channel-id to \"{slug}". |


***

If you like this and other linear containers for Channels that I have created, please consider supporting my work.

[![](https://pics.paypal.com/00/s/MDY0MzZhODAtNGI0MC00ZmU5LWI3ODYtZTY5YTcxOTNlMjRm/file.PNG)](https://www.paypal.com/donate/?hosted_button_id=BBUTPEU8DUZ6J)
