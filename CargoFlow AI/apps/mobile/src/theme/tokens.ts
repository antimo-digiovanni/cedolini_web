import { Platform } from 'react-native';

const headingFont = Platform.select({
  ios: 'AvenirNext-Bold',
  android: 'sans-serif-condensed',
  default: 'System',
});

const bodyFont = Platform.select({
  ios: 'AvenirNext-Regular',
  android: 'sans-serif-medium',
  default: 'System',
});

export const theme = {
  colors: {
    ink: '#102033',
    paper: '#f8f4ea',
    sand: '#e7d8ba',
    clay: '#c06c4d',
    ember: '#8f2d1f',
    pine: '#23463f',
    sky: '#9fc7c2',
    card: '#fffdf8',
    line: '#d6cab4',
    muted: '#5c645f',
  },
  radius: {
    lg: 28,
    md: 20,
    sm: 14,
  },
  font: {
    heading: headingFont,
    body: bodyFont,
  },
};
