FROM node:20-alpine

WORKDIR /app

# Copy everything first
COPY . .

# Install deps and build
RUN npm install && npm run build

# Install serve globally
RUN npm install -g serve

EXPOSE 3000

CMD ["serve", "-s", "dist", "-l", "3000"]
