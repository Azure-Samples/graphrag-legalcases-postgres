import React, { createContext, useState, ReactNode, FC } from 'react';
import { PAIDRetrievalMode } from "../api/models";

// Define the context's value type
interface AppStateContextType {
  sharedState: PAIDRetrievalMode;
  setSharedState: React.Dispatch<React.SetStateAction<PAIDRetrievalMode>>;
}

// Create the context with a default value of undefined
export const AppStateContext = createContext<AppStateContextType | undefined>(undefined);

// Create the AppStateProvider component to manage shared state
export const AppStateProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const [sharedState, setSharedState] = useState<PAIDRetrievalMode>(PAIDRetrievalMode.Vector);

  return (
    <AppStateContext.Provider value={{ sharedState, setSharedState }}>
      {children}
    </AppStateContext.Provider>
  );
};
