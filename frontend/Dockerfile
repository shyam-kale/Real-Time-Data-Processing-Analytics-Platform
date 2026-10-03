FROM node:20-alpine

WORKDIR /app

# bust cache
ARG CACHEBUST=1

# Copy all frontend files into container
COPY . .

# Install dependencies
RUN npm install

# Build the app
RUN npm run build

# Install serve to host the built app
RUN npm install -g serve

EXPOSE 3000

CMD ["serve", "-s", "dist", "-l", "3000"]
