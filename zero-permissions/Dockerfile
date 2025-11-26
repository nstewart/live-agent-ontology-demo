FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY zero-permissions/package*.json ./

# Install dependencies
RUN npm install

# Copy zero-permissions source files
COPY zero-permissions/update-permissions.ts ./
COPY zero-permissions/tsconfig.json ./
COPY zero-permissions/zero.config.json ./

# Copy schema from canonical location (web/src/schema.ts)
COPY web/src/schema.ts ./

# Run the update script
CMD ["npm", "run", "update"]
