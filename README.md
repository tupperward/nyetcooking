# Nyetcooking  
Did you know that NYT Cooking recipe pages have all the data for the recipe on the page in front of the paywall? Get all the good stuff without all the chuff.

## How To Build
1. [Install Go](https://go.dev/doc/install)
2. `go build -o nyetcooking`
3. Move to your bin `mv nyetcooking /usr/local/bin/nyetcooking`
4. (On windows, Move to System32 and add to PATH)

## How to Use
In your terminal type `nyetcooking <url>` and the HTML page will be generated in your current directory.

### Flags
- --url         Url to scrape
- -o            Output Path
- --no-image    Do not render image
