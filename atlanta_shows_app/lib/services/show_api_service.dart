// lib/services/show_api_service.dart

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:atlanta_shows_app/models/show.dart';
import 'dart:developer';

class ShowApiService {
  // Assuming the correct path is /events
  final String _baseUrl =
      'https://atlantashows-production.up.railway.app/events';

  Future<List<Show>> fetchShows() async {
    final uri = Uri.parse(_baseUrl);
    final response = await http.get(uri);

    // --- DEBUGGING LOGS ---
    // Use log() instead of print() for better output in Flutter
    log('API URL: $_baseUrl');
    log('Status Code: ${response.statusCode}');
    log('Response Body: ${response.body}');
    // ----------------------

    if (response.statusCode == 200) {
      // If the body is "No upcoming events found.", it's not a valid list.
      if (response.body.contains("No upcoming events found")) {
        // Return an empty list if the API explicitly says no events exist.
        return [];
      }

      // We expect the JSON body to be a List of objects: [...]
      final List<dynamic> jsonList = jsonDecode(response.body);

      // Map the raw JSON objects to our simple Show model
      return jsonList.map((showJson) {
        // ... (Parsing logic remains the same for now) ...
        final String rawDate = showJson['date'] ??
            showJson['event_date'] ??
            DateTime.now().toIso8601String();

        return Show(
          id: showJson['id'].toString(),
          title: showJson['title'] ??
              showJson['name'] ??
              'Unnamed Show (Key Error)',
          venue: showJson['venue'] ??
              showJson['location'] ??
              'Venue Unknown (Key Error)',
          date: DateTime.tryParse(rawDate) ?? DateTime.now(),
          imageUrl: showJson['imageUrl'] ?? showJson['image_url'] ?? '',
        );
      }).toList();
    } else {
      // Handle the server error (e.g., if the server is down or returns a 404/500)
      throw Exception(
          'Failed to load shows from Railway backend. Status: ${response.statusCode}.');
    }
  }
}
