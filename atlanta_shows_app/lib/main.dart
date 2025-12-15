import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:io';

// 🛑 Replace this placeholder with your actual Railway URL 🛑
// Example: 'https://atlantashows-production.up.railway.app'
const String API_BASE_URL = 'https://atlantashows-production.up.railway.app/';

void main() {
  runApp(const AtlantaShowsApp());
}

// --- Data Model for a Single Show ---
class Show {
  final String id;
  final String title;
  final String venue;
  final String date;
  final String imageUrl;

  Show({
    required this.id,
    required this.title,
    required this.venue,
    required this.date,
    required this.imageUrl,
  });

  factory Show.fromJson(Map<String, dynamic> json) {
    return Show(
      id: json['id'] ?? 'N/A',
      title: json['title'] ?? 'No Title',
      venue: json['venue'] ?? 'No Venue',
      date: json['date'] ?? 'No Date',
      imageUrl: json['imageUrl'] ?? 'https://via.placeholder.com/150',
    );
  }
}

// --- Fetching Logic ---
Future<List<Show>> fetchShows() async {
  final apiUrl = Uri.parse('$API_BASE_URL/events');
  String errorDetails = 'Unknown error.';

  try {
    final response = await http.get(apiUrl);

    if (response.statusCode == 200) {
      // The server is running and returned data
      List jsonList = jsonDecode(response.body);
      return jsonList.map((data) => Show.fromJson(data)).toList();
    } else {
      // Server is running, but returned an error status (e.g., 500)
      errorDetails = 'Failed to load shows from backend. Status: ${response.statusCode}. Body: ${response.body.substring(0, response.body.length > 100 ? 100 : response.body.length)}...';
      throw Exception(errorDetails);
    }
  } on SocketException {
    errorDetails = 'Network/Host error: Failed host lookup or no internet connection.';
    throw Exception(errorDetails);
  } on HttpException {
    errorDetails = 'HTTP error: Could not find the server.';
    throw Exception(errorDetails);
  } on FormatException {
    errorDetails = 'JSON parsing error: Server returned invalid data.';
    throw Exception(errorDetails);
  } catch (e) {
    // Catch any other exceptions, including the intentional ones thrown above
    if (e is Exception) {
      throw e; // Re-throw the custom exception
    }
    errorDetails = 'Exception during connection: ${e.toString()}';
    throw Exception(errorDetails);
  }
}

// --- Main Application Widget ---
class AtlantaShowsApp extends StatelessWidget {
  const AtlantaShowsApp({super.key});

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
  const ShowListScreen({super.key});

  @override
  State<ShowListScreen> createState() => _ShowListScreenState();
}

class _ShowListScreenState extends State<ShowListScreen> {
  late Future<List<Show>> futureShows;

  @override
  void initState() {
    super.initState();
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
        actions: [
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
                children: [
                  const Icon(Icons.error_outline, color: Colors.red, size: 60),
                  const Padding(
                    padding: EdgeInsets.all(8.0),
                    child: Text(
                      'CONNECTION FAILED',
                      style: TextStyle(color: Colors.red, fontSize: 18, fontWeight: FontWeight.bold),
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
                itemCount: snapshot.data!.length,
                itemBuilder: (context, index) {
                  Show show = snapshot.data![index];
                  return ListTile(
                    leading: show.imageUrl.isNotEmpty
                        ? Image.network(show.imageUrl, width: 50, height: 50, fit: BoxFit.cover)
                        : const Icon(Icons.music_note),
                    title: Text(show.title),
                    subtitle: Text('${show.venue} - ${show.date}'),
                    // Add tap handling or navigation here if needed
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