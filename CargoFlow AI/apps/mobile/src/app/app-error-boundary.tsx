import React from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { theme } from '../theme/tokens';

type AppErrorBoundaryProps = {
  children: React.ReactNode;
};

type AppErrorBoundaryState = {
  errorMessage: string | null;
};

export class AppErrorBoundary extends React.Component<AppErrorBoundaryProps, AppErrorBoundaryState> {
  state: AppErrorBoundaryState = {
    errorMessage: null,
  };

  static getDerivedStateFromError(error: Error): AppErrorBoundaryState {
    return {
      errorMessage: error.message || 'Errore runtime non gestito',
    };
  }

  componentDidCatch(error: Error) {
    console.error('CargoFlow UI crash:', error);
  }

  render() {
    if (this.state.errorMessage) {
      return (
        <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
          <View style={styles.card}>
            <Text style={styles.title}>UI runtime error</Text>
            <Text style={styles.message}>{this.state.errorMessage}</Text>
            <Text style={styles.hint}>Ricarica la pagina. Se l'errore resta, mandami questo messaggio esatto.</Text>
          </View>
        </ScrollView>
      );
    }

    return this.props.children;
  }
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: '#f7d9d9',
  },
  content: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: 24,
  },
  card: {
    backgroundColor: '#fff5f5',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#d88c8c',
    padding: 20,
    gap: 10,
  },
  title: {
    fontFamily: theme.font.heading,
    fontSize: 26,
    color: '#7f1d1d',
  },
  message: {
    fontFamily: theme.font.body,
    fontSize: 15,
    lineHeight: 22,
    color: '#7f1d1d',
  },
  hint: {
    fontFamily: theme.font.body,
    fontSize: 13,
    lineHeight: 20,
    color: '#5b2020',
  },
});