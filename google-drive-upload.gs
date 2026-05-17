/**
 * Hando Booth — Google Drive Upload Script
 *
 * SETUP INSTRUCTIONS:
 * 1. Go to https://script.google.com
 * 2. Create a new project, name it "Hando Booth Upload"
 * 3. Paste this entire file into Code.gs (replace the default content)
 * 4. Click Deploy > New deployment
 * 5. Type: "Web app"
 * 6. Execute as: "Me" (your account)
 * 7. Who has access: "Anyone" (so the app can reach it — but the TOKEN protects it)
 * 8. Click Deploy, authorize when prompted
 * 9. Copy the Web App URL — paste it into Hando Booth admin (Google Drive section)
 * 10. Also copy the TOKEN below and paste it into admin
 *
 * IMPORTANT: The TOKEN below is your secret key. Change it to something unique!
 */

const TOKEN = 'hando-booth-2025-secret'; // CHANGE THIS to your own secret
const ROOT_FOLDER_NAME = 'Hando Booth';

function doPost(e) {
  try {
    // Parse the request
    const data = JSON.parse(e.postData.contents);

    // Verify token
    if (data.token !== TOKEN) {
      return ContentService.createTextOutput(JSON.stringify({ ok: false, error: 'Invalid token' }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    // Get or create root folder
    const rootFolder = getOrCreateFolder(DriveApp.getRootFolder(), ROOT_FOLDER_NAME);

    // Get or create today's date folder (e.g., "2026-05-11")
    const today = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd');
    const dayFolder = getOrCreateFolder(rootFolder, today);

    // Decode the base64 file data
    const fileData = Utilities.base64Decode(data.fileData);
    const blob = Utilities.newBlob(fileData, data.mimeType, data.filename);

    // Save to Drive
    const file = dayFolder.createFile(blob);

    // Add description if provided
    if (data.description) {
      file.setDescription(data.description);
    }

    return ContentService.createTextOutput(JSON.stringify({
      ok: true,
      fileId: file.getId(),
      fileName: file.getName(),
      folder: today
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ ok: false, error: err.message }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function getOrCreateFolder(parent, name) {
  const folders = parent.getFoldersByName(name);
  if (folders.hasNext()) {
    return folders.next();
  }
  return parent.createFolder(name);
}

// Test function — run this to verify the script has Drive access
function testSetup() {
  const rootFolder = getOrCreateFolder(DriveApp.getRootFolder(), ROOT_FOLDER_NAME);
  Logger.log('Root folder created/found: ' + rootFolder.getName());
  Logger.log('Folder URL: ' + rootFolder.getUrl());
}
