import 'package:connectivity_plus/connectivity_plus.dart';

class NetworkStatus {
  NetworkStatus({required this.isOnline, this.type});
  final bool isOnline;
  final ConnectivityResult? type;
}

class NetworkMonitor {
  NetworkMonitor() {
    _connectivity = Connectivity();
  }

  late final Connectivity _connectivity;

  Stream<NetworkStatus> statusStream() async* {
    final current = await _connectivity.checkConnectivity();
    yield NetworkStatus(isOnline: _isOnline(current), type: current);
    yield* _connectivity.onConnectivityChanged
        .map((r) => NetworkStatus(isOnline: _isOnline(r), type: r));
  }

  bool _isOnline(ConnectivityResult result) =>
      result != ConnectivityResult.none;
}
