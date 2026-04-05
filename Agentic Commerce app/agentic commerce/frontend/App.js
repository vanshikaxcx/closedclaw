import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { StatusBar, View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { COLORS } from './theme/colors';
import { HomeScreen } from './screens/HomeScreen';
import { PayBotScreen } from './screens/PayBotScreen';

const Tab = createBottomTabNavigator();

const SimpleScreen = ({ route }) => (
  <View style={simpleStyles.container}>
    <Text style={simpleStyles.text}>{route.name}</Text>
  </View>
);

const simpleStyles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: COLORS.screenBg },
  text: { fontSize: 18, color: COLORS.textPrimary },
});

export default function App() {
  return (
    <SafeAreaProvider>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.navBg} />
      <NavigationContainer>
        <Tab.Navigator
          screenOptions={({ route }) => ({
            tabBarIcon: ({ focused, color, size }) => {
              let iconName;
              switch (route.name) {
                case 'Home': iconName = focused ? 'home' : 'home-outline'; break;
                case 'Pay': iconName = focused ? 'scan-circle' : 'scan-circle-outline'; break;
                case 'PayBot': iconName = focused ? 'chatbubbles' : 'chatbubbles-outline'; break;
                case 'History': iconName = focused ? 'receipt' : 'receipt-outline'; break;
                case 'Profile': iconName = focused ? 'person' : 'person-outline'; break;
                default: iconName = 'ellipse';
              }
              return <Ionicons name={iconName} size={size} color={color} />;
            },
            tabBarActiveTintColor: COLORS.paytmNavy,
            tabBarInactiveTintColor: COLORS.textSecondary,
            headerShown: false,
          })}
        >
          <Tab.Screen name="Home" component={HomeScreen} />
          <Tab.Screen name="Pay" component={SimpleScreen} />
          <Tab.Screen name="PayBot" component={PayBotScreen} />
          <Tab.Screen name="History" component={SimpleScreen} />
          <Tab.Screen name="Profile" component={SimpleScreen} />
        </Tab.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
