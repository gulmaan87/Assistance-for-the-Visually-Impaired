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
    yield NetworkStatus(
        isOnline: _isOnline(current), type: _getPrimaryType(current));
    yield* _connectivity.onConnectivityChanged.map((results) => NetworkStatus(
        isOnline: _isOnline(results), type: _getPrimaryType(results)));
  }

  bool _isOnline(List<ConnectivityResult> results) {
    return !results.contains(ConnectivityResult.none) && results.isNotEmpty;
  }

  ConnectivityResult? _getPrimaryType(List<ConnectivityResult> results) {
    if (results.isEmpty || results.contains(ConnectivityResult.none)) {
      return ConnectivityResult.none;
    }
    // Prefer wifi over mobile, etc.
    if (results.contains(ConnectivityResult.wifi))
      return ConnectivityResult.wifi;
    if (results.contains(ConnectivityResult.mobile))
      return ConnectivityResult.mobile;
    return results.first;
  }
}
