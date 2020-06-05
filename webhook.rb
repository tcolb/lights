require 'sinatra'
require 'json'
require_relative 'webhooksecret'

set :port, 3254

post '/payload' do
  request.body.rewind
  payload_body = request.body.read
  if verify_signature(payload_body)
    puts "Webhook signature matches, spawning update process..."
    pid = spawn("./update.sh")
    Process.detach(pid) 
  end
end

def verify_signature(payload_body)
  signature = 'sha1=' + OpenSSL::HMAC.hexdigest(OpenSSL::Digest.new('sha1'), WebhookSecret.secret, payload_body)
  return false, "Signatures didn't match!" unless Rack::Utils.secure_compare(signature, request.env['HTTP_X_HUB_SIGNATURE'])
  return true
end
