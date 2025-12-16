// lib/models/show.dart
import 'package:flutter/material.dart';

class Show {
  final String id;
  final String title;
  final String venue;
  final DateTime date;
  final String imageUrl; // Note: Your Python model doesn't supply this yet!

  // Cleaned up constructor for a data model
  const Show({
    required this.id,
    required this.title,
    required this.venue,
    required this.date,
    required this.imageUrl,
  });
  // Static method to create a list of placeholder shows for testing
  static List<Show> get mockShows {
    return [
      Show(
        id: '1',
        title: 'Atlanta Symphony Orchestra',
        venue: 'Atlanta Symphony Hall',
        date: DateTime(2025, 12, 20, 19, 30), // Example: Dec 20, 7:30 PM
        imageUrl: 'https://example.com/aso.jpg',
      ),
      Show(
        id: '2',
        title: 'Local Standup Night',
        venue: 'The Laughing Spot',
        date: DateTime(2025, 12, 21, 20, 0),
        imageUrl: 'https://example.com/standup.jpg',
      ),
      Show(
        id: '3',
        title: 'Indie Band Showcase',
        venue: 'The Masquerade',
        date: DateTime(2025, 12, 22, 19, 0),
        imageUrl: 'https://example.com/masq.jpg',
      ),
    ];
  }
}
