from scraper.crawler.regions import get_regions
from scraper.crawler.universities import get_universities
from scraper.crawler.directions import get_directions
from scraper.crawler.applicants import parse_direction


regions = get_regions()

for region in regions:

    print(region["name"])

    universities = get_universities(region["url"])

    for university in universities:

        print("  ", university["name"])

        directions = get_directions(university["url"])

        for direction in directions:

            print("     ", direction["name"])

            applicants = parse_direction(direction["url"])

            print(f"         {len(applicants)} applicants")