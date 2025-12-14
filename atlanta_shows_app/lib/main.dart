// lib/main.dart

import 'package:flutter/material.dart';
import 'package:atlanta_shows_app/models/show.dart';
import 'package:atlanta_shows_app/services/show_api_service.dart';

void main() {
  runApp(const AtlantaShowsApp());
}

// 1. Root Application Widget
class AtlantaShowsApp extends StatelessWidget {
  // Compatible constructor syntax (pre-Dart 2.15)
  const AtlantaShowsApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Atlanta Shows',
      theme: ThemeData(
        primarySwatch: Colors.blue,
      ),
      home: const HomeScreen(),
    );
  }
}

// 2. HomeScreen (Stateful part - manages the data fetching state)
class HomeScreen extends StatefulWidget {
  const HomeScreen({Key? key}) : super(key: key);

  @override
  // Creates the mutable state for this widget
  State<HomeScreen> createState() => _HomeScreenState();
}

// 3. State Class (Holds the data and logic)
class _HomeScreenState extends State<HomeScreen> {
  // State variables
  List<Show> _shows = [];
  bool _isLoading = true;
  String? _error;

  // Service instance
  final ShowApiService _apiService = ShowApiService();

  @override
  void initState() {
    super.initState();
    _fetchShowData();
  }

  // Asynchronous method to handle data fetching
  Future<void> _fetchShowData() async {
    // 1. Set loading state before fetching
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      // 2. Fetch data (This currently throws an error due to the dummy URL in the API service)
      final data = await _apiService.fetchShows();

      // 3. Update state with successful data
      setState(() {
        _shows = data;
        _isLoading = false;
      });
    } catch (e) {
      // 4. Handle errors (e.g., failed network request)
      setState(() {
        _error = e.toString();
        _isLoading = false;
        // Fallback to mock data on error for better UX
        _shows = Show.mockShows;
      });
    }
  }

  // 5. Build method
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Atlanta Local Shows'),
      ),
      body: _buildBody(), // Decide what to display (Loading, Error, or List)
      floatingActionButton: FloatingActionButton(
        onPressed: _fetchShowData, // Refresh data on button press
        child: const Icon(Icons.refresh),
      ),
    );
  }

  // 6. Helper method to render UI based on state
  Widget _buildBody() {
    if (_isLoading) {
      // Show loading indicator
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      // Show error message and try to display fallback data
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Text(
                '🔴 CONNECTION FAILED. Showing Mock Data.',
                textAlign: TextAlign.center,
                style: TextStyle(
                    color: Colors.red,
                    fontSize: 16,
                    fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 10),
              // DISPLAY THE FULL ERROR MESSAGE HERE:
              Text(
                'Error Details: $_error',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.black54, fontSize: 12),
              ),
              const SizedBox(height: 20),
              const Expanded(
                child: Text('--- Fallback Mock Data ---'),
              ),
              // We still display the mock data list below the error
              Expanded(
                child: _buildShowList(_shows),
              ),
            ],
          ),
        ),
      );
    }

    // Show the actual list of shows
    return _buildShowList(_shows);
  }

  // 7. Reusable List Builder
  Widget _buildShowList(List<Show> shows) {
    if (shows.isEmpty) {
      return const Center(child: Text('No shows available.'));
    }
    return ListView.builder(
      itemCount: shows.length,
      itemBuilder: (context, index) {
        final show = shows[index];
        return ListTile(
          leading: const Icon(Icons.calendar_today),
          title: Text(show.title),
          subtitle:
              Text('${show.venue} on ${show.date.month}/${show.date.day}'),
          trailing: const Icon(Icons.arrow_forward_ios),
          onTap: () {
            // TODO: Navigate to the detail screen
            debugPrint('Tapped on ${show.title}');
          },
        );
      },
    );
  }
}
