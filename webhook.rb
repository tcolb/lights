require 'sinatra'
require 'json'

require_relative 'webhooksecret'

set :port, 3254

pid = spawn("autossh -R lights-" + WebhookSecret.identity + ".serveo.net:80:localhost:3254 serveo.net")
Process.detach(pid)

post '/payload' do
  request.body.rewind
  payload_body = request.body.read
  if verify_signature(payload_body)
    puts "Webhook signature matches, pulling from git..."
    puts `git pull`
  end
end

def verify_signature(payload_body)
  signature = 'sha1=' + OpenSSL::HMAC.hexdigest(OpenSSL::Digest.new('sha1'), WebhookSecret.secret, payload_body)
  return false, "Signatures didn't match!" unless Rack::Utils.secure_compare(signature, request.env['HTTP_X_HUB_SIGNATURE'])
  return true
end
