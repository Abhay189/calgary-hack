import googlemaps
from datetime import datetime
from shapely.geometry import Point, LineString, mapping
import csv
import re
import html
import requests
from contextlib import closing
import boto3
import time
from pygame import mixer
import os
import pytz
import serial
import pynmea2

time_pattern = r'(\d+):(\d+)'
direction_pattern = r'\s*(nw|sw|ne|se)\s*'
bracket_pattern = r'\(.+\)'

def synthesize_speech(text):
    # Initialize Polly client
    polly_client = boto3.client('polly', region_name='us-east-1', aws_access_key_id='aws_access_key_id', aws_secret_access_key='aws_secret_access_key')
    
    # Synthesize speech
    response = polly_client.synthesize_speech(VoiceId='Joanna', OutputFormat='mp3', Text=text)
    
    # Generate a unique filename using the current timestamp
    timestamp = int(time.time())
    filename = f"speech_{timestamp}.mp3"
    
    with closing(response['AudioStream']) as stream:
        with open(filename, "wb") as file:
            file.write(stream.read())

    # Initialize mixer only once or ensure it's not already initialized
    if not mixer.get_init():
        mixer.init()

    mixer.music.load(filename)
    mixer.music.play()

    # Wait for the audio to finish playing
    while mixer.music.get_busy():
        pass

    # Stop and unload the music
    mixer.music.stop()
    mixer.music.unload()  # If using Pygame 2.0.0 or newer, ensures the file is unloaded

    # Quit the mixer (optional, see note below)
    mixer.quit()

    # Delete the file after ensuring it's no longer in use
    try:
        os.remove(filename)
    except PermissionError as e:
        print(f"Error removing the file: {e}")

def read_traffic_signals(csv_file):
    with open(csv_file, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        return [Point(float(row['longitude']), float(row['latitude'])) for row in reader]

# def read_gps(): # for respberry pi gps tracking
#     # Open serial port
#     port = "/dev/ttyS0"
#     ser = serial.Serial(port, baudrate=9600, timeout=0.5)

#     while True:
#         data = ser.readline()
#         # Try decoding the bytes to a string
#         try:
#             data = data.decode("ascii", errors="replace")
#         except UnicodeDecodeError:
#             continue  # If decode fails, try reading the next line
        
#         # Check if the read line is a GGA NMEA sentence (Global Positioning System Fix Data)
#         if data.startswith('$GNGGA') or data.startswith('$GPGGA'):
#             try:
#                 msg = pynmea2.parse(data)
#                 # Now msg contains structured GPS data you can use
#                 print(f"Latitude: {msg.latitude}, Longitude: {msg.longitude}")
#                 print(f"Time: {msg.timestamp}, Altitude: {msg.altitude} {msg.altitude_units}")
#                 break  # Remove this if you want to continuously read
#             except pynmea2.ParseError:
#                 print("Error parsing NMEA sentence")
#                 continue

def get_route_line(gmaps_client, start, end):
    directions_result = gmaps_client.directions(start, end)
    polyline = directions_result[0]['overview_polyline']['points']
    path = googlemaps.convert.decode_polyline(polyline)
    return LineString([(p['lng'], p['lat']) for p in path])

def find_signals_on_route(route_line, signals, threshold):
    return [signal for signal in signals if route_line.distance(signal) <= threshold]

def integrate_signals_into_instructions(steps, signals, threshold):
    # Iterate over each step in the walking directions
    for step_index, step in enumerate(steps):
        # Convert step start and end locations to Shapely Points
        step_start_point = Point(step['start_location']['lng'], step['start_location']['lat'])
        step_end_point = Point(step['end_location']['lng'], step['end_location']['lat'])
        # Create a LineString from start to end point of the step
        step_line = LineString([step_start_point, step_end_point])
        
        # Check each traffic signal for proximity to the current step
        for signal in signals:
            if step_line.distance(signal) <= threshold:
                # The signal is close to this step, modify the instruction to include traffic signal information
                if 'instruction' not in step:
                    step['instruction'] = ""
                step['instruction'] += " Stop! traffic signal detected."
                step['instruction'] += " Now, cross the signal"
    
    # Return steps with modified instructions
    return steps

def print_walking_instructions_with_signal(gmaps_client, start_location, end_location, signals_on_route, threshold_distance):
    walking_directions = gmaps_client.directions(start_location, end_location, mode="walking")
    if walking_directions:
        steps = walking_directions[0]['legs'][0]['steps']
        steps_with_signals = integrate_signals_into_instructions(steps, signals_on_route, threshold_distance)
        
        for step in steps_with_signals:
            instructions = strip_html_tags(step.get('html_instructions', ''))
            instructions = refine_instructions(instructions)
            instructions = re.sub(direction_pattern, ' ', instructions)
            distance = convert_distance_to_steps(step['distance']['text'])
            
            # Formulate the base walking instruction
            base_instruction = f"{instructions}. Walk for {distance}."
            print(f" - {base_instruction}")
            synthesize_speech(base_instruction)
            
            # Check for and handle additional signal instructions
            if 'instruction' in step and "Stop! traffic signal detected." in step['instruction']:
                # Synthesize the stop signal detected message
                stop_signal_instruction = "Stop! traffic signal detected."
                print("Stop! traffic signal detected.")
                synthesize_speech(stop_signal_instruction)
                
                # Introduce a delay
                time.sleep(0.25)  # Pause for 0.5 seconds
                
                # Synthesize the "Now, cross the signal." message
                cross_signal_instruction = "Now, cross the signal."
                print("Now, cross the signal.")
                synthesize_speech(cross_signal_instruction)


def reverse_geocode(lat, lng):
    # Replace YOUR_API_KEY with your actual Google Maps API key
    api_key = "api_key"
    base_url = "https://maps.googleapis.com/maps/api/geocode/json?"
    endpoint = f"{base_url}latlng={lat},{lng}&key={api_key}"
    response = requests.get(endpoint)
    if response.status_code == 200:
        results = response.json()['results']
        if results:
            # Return the first result's formatted address
            return results[0]['formatted_address']
        else:
            return "Address not found"
    else:
        return "Error: Unable to connect to the API"

def strip_html_tags(html_text):
    """Remove HTML tags from a string."""
    clean_text = re.sub('<.*?>', '', html_text)
    return clean_text

def approximate_signals(instruction):
    """Heuristic to identify potential traffic signals in walking instructions."""
    signals_keywords = ['cross', 'intersection', 'traffic light']
    signal_hint = ""
    if any(keyword in instruction.lower() for keyword in signals_keywords):
        signal_hint = "You may encounter a signal."
    return signal_hint

def convert_distance_to_steps(distance_text):
    """Convert distance from km to meters if less than 1 km, ensuring all walking distances are in meters."""
    if ' km' in distance_text:
        distance_value = float(distance_text.replace(' km', '')) * 1000
        max_steps = int(distance_value/0.78)
        min_steps = int(distance_value/0.7)
        avg_steps = round((max_steps+min_steps)/20)*10
        return f"{avg_steps} steps"
    if ' m' in distance_text:
        distance_value = float(distance_text.replace(' m', ''))
        max_steps = int(distance_value/0.78)
        min_steps = int(distance_value/0.7)
        avg_steps = round((max_steps+min_steps)/20)*10
        return f"{avg_steps} steps"
    return distance_text  # Fallback, should not hit

def refine_instructions(instruction):
    """Refine instruction text to focus on actions and directions, minimizing road name details."""
    # Remove explicit mention of road names, trying to preserve only the action and direction
    instruction = re.sub(r'\bon\b [^\s]+', '', instruction)  # Remove 'on [road]'
    instruction = re.sub(r'\bonto\b [^\s]+', '', instruction)  # Remove 'onto [road]'
    instruction = re.sub(r'\bat\b [^\s]+', '', instruction)  # Remove 'at [road]'
    instruction = re.sub(r'\btoward\b [^\s]+', '', instruction)  # Remove 'toward [road]'
    instruction = re.sub(r'\bto\b [^\s]+', '', instruction)  # Remove 'to [road]'
    instruction = re.sub(r'\bfrom\b [^\s]+', '', instruction)  # Remove 'from [road]'
    instruction = re.sub(r'\bvia\b [^\s]+', '', instruction)  # Remove 'via [road]'
    instruction = re.sub(r'\b(st|rd|ave|blvd|dr|trl|lane|way|ct|pl)\b', '', instruction, flags=re.IGNORECASE)  # Remove common road type abbreviations
    
    # Normalize and clean up the instruction text
    instruction = re.sub(' +', ' ', instruction)  # Replace multiple spaces with a single space
    instruction = instruction.strip().capitalize()

    return instruction

def print_walking_instructions(gmaps_client, start_location, end_location):
    """Print detailed walking instructions with enhanced cleaning for clarity."""
    walking_directions = gmaps_client.directions(start_location, end_location, mode="walking")
    if walking_directions:
        steps = walking_directions[0]['legs'][0]['steps']
        for step in steps:
            instructions = strip_html_tags(step['html_instructions'])
            instructions = refine_instructions(instructions)
            instructions = re.sub(direction_pattern, ' ', instructions)
            distance = convert_distance_to_steps(step['distance']['text'])
            print(f" - {instructions}. Walk for {distance}.")
            synthesize_speech(instructions+" walk for "+ distance)

def refine_address(address):
    # Define patterns to remove: directions and unit numbers
    directions = [" NE", " SE", " NW", " SW"]
    unit_number_pattern = r"\s#\d+"
    
    # Split the address at the comma to isolate the street address
    parts = address.split(',')
    street_address = parts[0]
    
    # Remove any details in parentheses
    street_address = street_address.split('(')[0].strip()
    
    # Remove directional indicators
    for direction in directions:
        street_address = street_address.replace(direction, '')
    
    # Remove unit numbers
    street_address = re.sub(unit_number_pattern, '', street_address)
    
    return street_address.strip()

def print_transit_instructions(step):
    """Print detailed transit instructions, including vehicle type, line name, number of stops, and timing, with corrected time difference calculation."""
    # Assuming transit_details['departure_time']['value'] is a timestamp
    departure_time_value = step['transit_details']['departure_time']['value']
    departure_datetime = datetime.fromtimestamp(departure_time_value)  # Convert timestamp to datetime
    
    # Current time
    now = datetime.now()
    
    transit_details = step['transit_details']
    vehicle_name = transit_details['line']['vehicle']['name']
    departure_stop = transit_details['departure_stop']['name']
    arrival_stop = transit_details['arrival_stop']['name']
    departure_time = departure_datetime.strftime('%I:%M %p')  # Format time as needed
    arrival_time = step['transit_details']['arrival_time']['text']
    bus_name = transit_details['line']['name']
    bus_number = transit_details['line']['short_name']
    num_stops = step.get('num_stops') # Extract the number of stops
    
    # Calculate time difference
    time_diff = departure_datetime - now
    time_diff_seconds = time_diff.total_seconds()
    time_diff_hours = int(time_diff_seconds // 3600)
    time_diff_minutes = int((time_diff_seconds % 3600) // 60)
    
    # Clean up stop names
    departure_stop = re.sub(bracket_pattern, '', departure_stop)
    arrival_stop = re.sub(bracket_pattern, '', arrival_stop)
    
    # Construct the announcement, including the number of stops if available
    if num_stops is not None:
        stops_info = f" Ride bus for {num_stops} stops"
    else:
        stops_info = ""
    
    announcement = f"Take the {vehicle_name} number {bus_number}, {bus_name}, from {departure_stop} to {arrival_stop}{stops_info}. The {vehicle_name} arrives at {departure_time} in {time_diff_hours} hours and {time_diff_minutes} minutes, You will reach your destination by {arrival_time}."
    
    print(announcement)
    synthesize_speech(announcement)

    # Assuming a mechanism to trigger this based on GPS location:
    time.sleep(1)  # This delay is illustrative; actual implementation may vary
    synthesize_speech(f"Get off the {vehicle_name} now!")  # Announced based on GPS location

def get_detailed_route_instructions(gmaps_client, start, end, signals_on_route, threshold_distance):
    """Request and print detailed route instructions, integrating walking and transit directions with enhanced details, now including traffic signals."""
    directions_result = gmaps_client.directions(start, end, mode="transit", departure_time=datetime.now(), alternatives=False)

    if not directions_result:
        print("No routes found.")
        return

    print("Navigation Instructions:\n")
    for leg in directions_result[0]['legs']:
        for step in leg['steps']:
            if step['travel_mode'] == 'WALKING':
                start_lat_lng = f"{step['start_location']['lat']},{step['start_location']['lng']}"
                end_lat_lng = f"{step['end_location']['lat']},{step['end_location']['lng']}"

                start_location_name = reverse_geocode(step['start_location']['lat'], step['start_location']['lng'])
                end_location_name = reverse_geocode(step['end_location']['lat'], step['end_location']['lng'])

                print(f"You need to walk from {refine_address(start_location_name)} to {refine_address(end_location_name)}. Let's begin!")
                synthesize_speech("You need to walk from " + refine_address(start_location_name) + " to " + refine_address(end_location_name) + ". Let's begin!")
                
                # Call the updated function with signals and threshold
                print_walking_instructions_with_signal(gmaps_client, start_lat_lng, end_lat_lng, signals_on_route, threshold_distance)
                
            elif step['travel_mode'] == 'TRANSIT':
                print_transit_instructions(step)
            print("-----\n")
    synthesize_speech("You have arrived at your destination!")



# Configuration
api_key = 'AIzaSyBUOkENWCASVyyH1Qq0bB67-ooJFEPCCio'
gmaps_client = googlemaps.Client(key=api_key)

# start_location = "24 23 St. NW, Calgary, AB, Canada"
# end_location = "University District, 4019 University Ave NW, Calgary, AB T3B 6K3"

# start_location = "5306 32 Ave NW, Calgary, AB, Canada"
# end_location = "University District, 4019 University Ave NW, Calgary, AB T3B 6K3"

start_location = "University District, 4019 University Ave NW, Calgary, AB T3B 6K3"
end_location = "101 9 Ave SW, Calgary, AB T2P 1J9"

csv_file_path = 'Traffic_Signals.csv'
threshold_distance = 0.001  # Adjust the threshold distance as needed

# Get the route line
route_line = get_route_line(gmaps_client, start_location, end_location)

# Read the traffic signals from CSV
traffic_signals = read_traffic_signals(csv_file_path)

# Find the traffic signals that are on the route
signals_on_route = find_signals_on_route(route_line, traffic_signals, threshold_distance)


print(get_detailed_route_instructions(gmaps_client, start_location, end_location,signals_on_route, threshold_distance))