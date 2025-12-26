import 'package:uuid/uuid.dart';

class Session {
  Session() : _uuid = const Uuid();
  final Uuid _uuid;

  String newIdempotencyKey() => _uuid.v4();
}





