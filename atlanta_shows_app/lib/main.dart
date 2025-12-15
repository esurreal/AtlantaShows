import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:io';

// 🛑 Replace this placeholder with your actual Railway URL 🛑
const String API_BASE_URL = 'https://YOUR-RAILWAY-DOMAIN.up.railway.app';

void main() {
  runApp(const AtlantaShowsApp());
}

// --- Data Model for a Single Show (Pre-Null Safety) ---
class Show {
  final String id;
  final String title;
  final String venue;
  final String date;
  final String imageUrl;

  Show({this.id, this.title, this.venue, this.date, this.imageUrl});

  factory Show.fromJson(Map<String, dynamic> json) {
    // In pre-null safety, you must rely on the data being present or handle null
    return Show(
      id: json['id'],
      title: json['title'],
      venue: json['venue'],
      date: json['date'],
      imageUrl: json['imageUrl'],
    );
  }
}

// --- Fetching Logic ---
Future<List<Show>> fetchShows() async {
  // Check the URL for validity before trying to parse
  if (API_BASE_URL
      .contains('https://atlantashows-production.up.railway.app/')) {
    throw Exception('API_BASE_URL is not set to your live Railway domain.');
  }

  final apiUrl = Uri.parse('$API_BASE_URL/events');
  String errorDetails = 'Unknown error.';

  try {
    final response = await http.get(apiUrl);

    if (response.statusCode == 200) {
      // The server is running and returned data
      List jsonList = jsonDecode(response.body);
      // Ensure the response is a list before mapping
      if (jsonList is List) {
        return jsonList.map((data) => Show.fromJson(data)).toList();
      } else {
        errorDetails = 'Server returned a single object, expected a list.';
        throw Exception(errorDetails);
      }
    } else {
      // Server is running, but returned an error status (e.g., 500)
      errorDetails =
          'Failed to load shows from backend. Status: ${response.statusCode}. Body: ${response.body.substring(0, response.body.length > 100 ? 100 : response.body.length)}...';
      throw Exception(errorDetails);
    }
  } on SocketException {
    errorDetails =
        'Network/Host error: Failed host lookup or no internet connection.';
    throw Exception(errorDetails);
  } on HttpException {
    errorDetails = 'HTTP error: Could not find the server.';
    throw Exception(errorDetails);
  } on FormatException {
    errorDetails = 'JSON parsing error: Server returned invalid data.';
    throw Exception(errorDetails);
  } catch (e) {
    errorDetails = 'Exception during connection: ${e.toString()}';
    throw Exception(errorDetails);
  }
}

// --- Main Application Widget ---
class AtlantaShowsApp extends StatelessWidget {
  // Pre-Null Safety Constructor
  const AtlantaShowsApp({Key key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Atlanta Shows',
      theme: ThemeData(
        primarySwatch: Colors.blue,
      ),
      home: const ShowListScreen(),
    );
  }
}

// --- Screen Widget to Display Data ---
class ShowListScreen extends StatefulWidget {
  // Pre-Null Safety Constructor
  const ShowListScreen({Key key}) : super(key: key);

  @override
  State<ShowListScreen> createState() => _ShowListScreenState();
}

class _ShowListScreenState extends State<ShowListScreen> {
  // Initialized now instead of using 'late'
  Future<List<Show>> futureShows;

  @override
  void initState() {
    super.initState();
    // Initialize the Future in initState, which is safe in pre-null safety
    futureShows = fetchShows();
  }

  // Helper function to simulate a refresh
  void _onRefresh() {
    setState(() {
      futureShows = fetchShows();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Atlanta Shows'),
        actions: <Widget>[
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _onRefresh,
          ),
        ],
      ),
      body: Center(
        child: FutureBuilder<List<Show>>(
          future: futureShows,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const CircularProgressIndicator();
            } else if (snapshot.hasError) {
              // Display the actual error details to the user for debugging
              return Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: <Widget>[
                  const Icon(Icons.error_outline, color: Colors.red, size: 60),
                  const Padding(
                    padding: EdgeInsets.all(8.0),
                    child: Text(
                      'CONNECTION FAILED',
                      style: TextStyle(
                          color: Colors.red,
                          fontSize: 18,
                          fontWeight: FontWeight.bold),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 20.0),
                    child: Text(
                      'Error Details: ${snapshot.error}',
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 14),
                    ),
                  ),
                  const SizedBox(height: 20),
                  ElevatedButton(
                    onPressed: _onRefresh,
                    child: const Text('Try Again'),
                  ),
                ],
              );
            } else if (snapshot.hasData) {
              // Successfully received data
              return ListView.builder(
                // No ! operator needed in pre-null safety
                itemCount: snapshot.data.length,
                itemBuilder: (context, index) {
                  // No ! operator needed in pre-null safety
                  Show show = snapshot.data[index];
                  return ListTile(
                    leading: show.imageUrl != null
                        ? Image.network(show.imageUrl,
                            width: 50, height: 50, fit: BoxFit.cover)
                        : const Icon(Icons.music_note),
                    title: Text(show.title ?? 'Unknown Title'),
                    subtitle: Text(
                        '${show.venue ?? 'Unknown Venue'} - ${show.date ?? 'Unknown Date'}'),
                  );
                },
              );
            } else {
              return const Text('No data found.');
            }
          },
        ),
      ),
    );
  }
}
